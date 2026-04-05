import os
import re
import discord
from discord.ext import commands, tasks
from datetime import datetime
import aiohttp
from aiohttp import web
import asyncio
import json

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbw2tywG42XA7R8bFq_XPF-S2QjU5eTKpDBa59KnNukWfpPOXU3UJIR-emVvMZURuK0O/exec'
CANAL_ANIVERSARIO = 'chat-vendetta'

_aniversarios_enviados: dict[str, str] = {}  # {discord_id: 'DD/MM do dia enviado'}


async def sheets_request(payload: dict):
    params = {'data': json.dumps(payload, ensure_ascii=False)}
    async with aiohttp.ClientSession() as session:
        async with session.get(APPS_SCRIPT_URL, params=params) as resp:
            text = await resp.text()
            print(f'sheets resposta: {text}')
            return json.loads(text) if text.strip() else None


async def sheets_get_vendedores() -> list:
    result = await sheets_request({'aba': 'LerVendedores'})
    return result if isinstance(result, list) else []


async def sheets_get_aniversarios() -> list:
    result = await sheets_request({'aba': 'LerAniversarios'})
    return result if isinstance(result, list) else []


# ── LAVAGEM ───────────────────────────────────────────────────────────────────

class LavagemModal(discord.ui.Modal, title='Cálculo de Lavagem'):
    nome = discord.ui.TextInput(label='Nome', placeholder='Ex: João Silva', required=True)
    valor_sujo = discord.ui.TextInput(label='Valor Sujo', placeholder='Ex: 10000', required=True)
    margem_venda = discord.ui.TextInput(label='Taxa Cobrada do Cliente (%)', placeholder='Ex: 30', required=True)
    margem_maquina = discord.ui.TextInput(label='Custo da Máquina (%)', placeholder='Ex: 10', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            nome = self.nome.value
            valor_sujo = float(self.valor_sujo.value.replace(',', '.'))
            margem_venda = float(self.margem_venda.value.replace(',', '.'))
            margem_maquina = float(self.margem_maquina.value.replace(',', '.'))

            taxa_cobrada = valor_sujo * (margem_venda / 100)
            custo_maquina = valor_sujo * (margem_maquina / 100)
            lucro = taxa_cobrada - custo_maquina
            valor_limpo = valor_sujo - taxa_cobrada

            embed = discord.Embed(title='🧼 Cálculo de Lavagem', color=0x2ECC71)
            embed.add_field(name='👤 Nome', value=nome, inline=False)
            embed.add_field(name='💵 Valor Sujo', value=f'R$ {valor_sujo:,.2f}', inline=False)
            embed.add_field(name='📤 Taxa Cobrada do Cliente', value=f'R$ {taxa_cobrada:,.2f} ({margem_venda}%)', inline=True)
            embed.add_field(name='⚙️ Custo da Máquina', value=f'R$ {custo_maquina:,.2f} ({margem_maquina}%)', inline=True)
            embed.add_field(name='✅ Valor Limpo (cliente recebe)', value=f'R$ {valor_limpo:,.2f}', inline=False)
            embed.add_field(name='💰 Seu Lucro', value=f'R$ {lucro:,.2f} ({margem_venda - margem_maquina:.0f}%)', inline=False)

            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message(
                '❌ Valores inválidos. Use apenas números nos campos de valor e porcentagem.',
                ephemeral=True,
            )


@bot.tree.command(name='lavagem', description='Abre o formulário de cálculo de lavagem')
async def lavagem(interaction: discord.Interaction):
    await interaction.response.send_modal(LavagemModal())


# ── VENDA ─────────────────────────────────────────────────────────────────────

class VendaModal(discord.ui.Modal, title='Registro de Venda'):
    nome = discord.ui.TextInput(label='Nome', placeholder='Ex: João Silva', required=True)
    data = discord.ui.TextInput(label='Data', placeholder='Ex: 25/02/2026', required=True)
    item = discord.ui.TextInput(label='Item', placeholder='Ex: Produto X', required=True)
    quantidade = discord.ui.TextInput(label='Quantidade', placeholder='Ex: 10', required=True)
    total = discord.ui.TextInput(label='Total (R$)', placeholder='Ex: 5000', required=True)

    def __init__(self, vendedor: str):
        super().__init__()
        self.vendedor = vendedor

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            registrado_em = datetime.now().strftime('%d/%m/%Y %H:%M')
            await sheets_request({
                'aba': 'Vendas',
                'nome': self.nome.value,
                'data': self.data.value,
                'item': self.item.value,
                'quantidade': self.quantidade.value,
                'total': self.total.value,
                'vendedor': self.vendedor,
                'registrado_em': registrado_em,
            })

            embed = discord.Embed(title='🛒 Venda Registrada', color=0x3498DB)
            embed.add_field(name='👤 Nome', value=self.nome.value, inline=True)
            embed.add_field(name='📅 Data', value=self.data.value, inline=True)
            embed.add_field(name='📦 Item', value=self.item.value, inline=False)
            embed.add_field(name='🔢 Quantidade', value=self.quantidade.value, inline=True)
            embed.add_field(name='💵 Total', value=f'R$ {self.total.value}', inline=True)
            embed.add_field(name='🧑‍💼 Vendedor', value=self.vendedor, inline=False)
            embed.set_footer(text=f'Registrado em {registrado_em}')

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao registrar venda: {e}', ephemeral=True)


class VendedorSelect(discord.ui.Select):
    def __init__(self, vendedores: list):
        options = [discord.SelectOption(label=v, value=v) for v in vendedores]
        super().__init__(placeholder='Selecione o vendedor...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VendaModal(self.values[0]))


class VendedorView(discord.ui.View):
    def __init__(self, vendedores: list):
        super().__init__()
        self.add_item(VendedorSelect(vendedores))


@bot.tree.command(name='venda', description='Registra uma nova venda')
async def venda(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        vendedores = await sheets_get_vendedores()
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao conectar ao Google Sheets: {e}', ephemeral=True)
        return

    if not vendedores:
        await interaction.followup.send(
            '❌ Nenhum vendedor cadastrado. Use `/vendedor` para cadastrar um.',
            ephemeral=True,
        )
        return

    await interaction.followup.send('Selecione o vendedor:', view=VendedorView(vendedores), ephemeral=True)


# ── VENDEDOR ──────────────────────────────────────────────────────────────────

@bot.tree.command(name='vendedor', description='Cadastra um novo vendedor')
@discord.app_commands.describe(nome='Nome do vendedor')
async def vendedor(interaction: discord.Interaction, nome: str):
    await interaction.response.defer(ephemeral=True)
    try:
        vendedores = await sheets_get_vendedores()
        if nome in vendedores:
            await interaction.followup.send(f'❌ Vendedor **{nome}** já está cadastrado.', ephemeral=True)
            return

        await sheets_request({
            'aba': 'Vendedores',
            'nome': nome,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
        })
        await interaction.followup.send(f'✅ Vendedor **{nome}** cadastrado com sucesso!', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao cadastrar vendedor: {e}', ephemeral=True)


# ── REMOVER VENDEDOR ──────────────────────────────────────────────────────────

class RemoverVendedorSelect(discord.ui.Select):
    def __init__(self, vendedores: list):
        options = [discord.SelectOption(label=v, value=v) for v in vendedores]
        super().__init__(placeholder='Selecione o vendedor para remover...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        nome = self.values[0]
        await interaction.response.defer(ephemeral=True)
        try:
            await sheets_request({'aba': 'RemoverVendedor', 'nome': nome})
            await interaction.followup.send(f'✅ Vendedor **{nome}** removido com sucesso!', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao remover vendedor: {e}', ephemeral=True)


class RemoverVendedorView(discord.ui.View):
    def __init__(self, vendedores: list):
        super().__init__()
        self.add_item(RemoverVendedorSelect(vendedores))


@bot.tree.command(name='vendedor_remover', description='Remove um vendedor cadastrado')
async def vendedor_remover(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        vendedores = await sheets_get_vendedores()
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao conectar ao Google Sheets: {e}', ephemeral=True)
        return

    if not vendedores:
        await interaction.followup.send('❌ Nenhum vendedor cadastrado.', ephemeral=True)
        return

    await interaction.followup.send('Selecione o vendedor para remover:', view=RemoverVendedorView(vendedores), ephemeral=True)


# ── EDITAR VENDEDOR ───────────────────────────────────────────────────────────

class EditarVendedorModal(discord.ui.Modal, title='Editar Vendedor'):
    def __init__(self, nome_atual: str):
        super().__init__()
        self.nome_atual = nome_atual
        self.novo_nome = discord.ui.TextInput(
            label='Novo Nome',
            default=nome_atual,
            required=True,
        )
        self.add_item(self.novo_nome)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await sheets_request({
                'aba': 'EditarVendedor',
                'nome_atual': self.nome_atual,
                'nome_novo': self.novo_nome.value,
            })
            await interaction.followup.send(
                f'✅ Vendedor **{self.nome_atual}** renomeado para **{self.novo_nome.value}**!',
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao editar vendedor: {e}', ephemeral=True)


class EditarVendedorSelect(discord.ui.Select):
    def __init__(self, vendedores: list):
        options = [discord.SelectOption(label=v, value=v) for v in vendedores]
        super().__init__(placeholder='Selecione o vendedor para editar...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditarVendedorModal(self.values[0]))


class EditarVendedorView(discord.ui.View):
    def __init__(self, vendedores: list):
        super().__init__()
        self.add_item(EditarVendedorSelect(vendedores))


@bot.tree.command(name='vendedor_editar', description='Edita o nome de um vendedor cadastrado')
async def vendedor_editar(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        vendedores = await sheets_get_vendedores()
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao conectar ao Google Sheets: {e}', ephemeral=True)
        return

    if not vendedores:
        await interaction.followup.send('❌ Nenhum vendedor cadastrado.', ephemeral=True)
        return

    await interaction.followup.send('Selecione o vendedor para editar:', view=EditarVendedorView(vendedores), ephemeral=True)


# ── CRAFT ────────────────────────────────────────────────────────────────────

async def sheets_get_craft_itens() -> list:
    result = await sheets_request({'aba': 'LerCraftItens'})
    return result if isinstance(result, list) else []


async def sheets_get_craft(item: str) -> list:
    result = await sheets_request({'aba': 'LerCraft', 'item': item})
    return result if isinstance(result, list) else []


async def craft_autocomplete(interaction: discord.Interaction, current: str) -> list:
    try:
        itens = await sheets_get_craft_itens()
    except Exception:
        return []
    filtered = [i for i in itens if current.lower() in i.lower()]
    return [discord.app_commands.Choice(name=i, value=i) for i in filtered[:25]]


@bot.tree.command(name='craft', description='Mostra os materiais necessários para craftar um item')
@discord.app_commands.describe(item='Nome do item (ex: M1911)', quantidade='Quantidade a craftar (padrão: 1)')
@discord.app_commands.autocomplete(item=craft_autocomplete)
async def craft(interaction: discord.Interaction, item: str, quantidade: int = 1):
    if quantidade < 1:
        await interaction.response.send_message('❌ A quantidade deve ser pelo menos 1.', ephemeral=True)
        return

    await interaction.response.defer()
    try:
        materiais = await sheets_get_craft(item)
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar craft: {e}', ephemeral=True)
        return

    if not materiais:
        await interaction.followup.send(
            f'❌ Item **{item}** não encontrado. Use `/craft_lista` para ver os itens disponíveis.',
            ephemeral=True,
        )
        return

    try:
        lista = '\n'.join(
            f'• **{m["material"]}** — {int(m["quantidade"]) * quantidade}x' for m in materiais
        )
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao calcular materiais: {e}', ephemeral=True)
        return

    titulo = f'🔧 Craft: {item}' if quantidade == 1 else f'🔧 Craft: {item} ×{quantidade}'
    embed = discord.Embed(title=titulo, description=lista, color=0xE67E22)
    embed.set_footer(text='Dados da planilha de crafts')
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='craft_lista', description='Lista todos os itens disponíveis para craft')
async def craft_lista(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        itens = await sheets_get_craft_itens()
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar itens: {e}', ephemeral=True)
        return

    if not itens:
        await interaction.followup.send('❌ Nenhum item cadastrado na planilha de crafts.', ephemeral=True)
        return

    lista = '\n'.join(f'• {i}' for i in sorted(itens))
    embed = discord.Embed(title='📋 Itens Disponíveis para Craft', description=lista, color=0xE67E22)
    await interaction.followup.send(embed=embed)


# ── COMPRAS ───────────────────────────────────────────────────────────────────

class CompraModal(discord.ui.Modal, title='Registro de Compra'):
    item = discord.ui.TextInput(label='Item Comprado', placeholder='Ex: AK-47, Colete, Droga X', required=True)
    quantidade = discord.ui.TextInput(label='Quantidade', placeholder='Ex: 5', required=True)
    valor = discord.ui.TextInput(label='Valor Pago (R$)', placeholder='Ex: 15000', required=True)
    observacao = discord.ui.TextInput(label='Observação (opcional)', placeholder='Ex: Comprado do NPC, fornecedor etc.', required=False)

    def __init__(self, comprador: str):
        super().__init__()
        self.comprador = comprador

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            registrado_em = datetime.now().strftime('%d/%m/%Y %H:%M')
            await sheets_request({
                'aba': 'Compras',
                'comprador': self.comprador,
                'item': self.item.value,
                'quantidade': self.quantidade.value,
                'valor': self.valor.value,
                'observacao': self.observacao.value or '-',
                'registrado_em': registrado_em,
            })

            embed = discord.Embed(title='🛍️ Compra Registrada', color=0x9B59B6)
            embed.add_field(name='👤 Comprador', value=self.comprador, inline=True)
            embed.add_field(name='📅 Data', value=registrado_em, inline=True)
            embed.add_field(name='📦 Item', value=self.item.value, inline=False)
            embed.add_field(name='🔢 Quantidade', value=self.quantidade.value, inline=True)
            embed.add_field(name='💵 Valor Pago', value=f'R$ {self.valor.value}', inline=True)
            if self.observacao.value:
                embed.add_field(name='📝 Observação', value=self.observacao.value, inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao registrar compra: {e}', ephemeral=True)


@bot.tree.command(name='compra', description='Registra uma nova compra')
async def compra(interaction: discord.Interaction):
    await interaction.response.send_modal(CompraModal(interaction.user.display_name))


@bot.tree.command(name='compras_listar', description='Lista o histórico de compras')
@discord.app_commands.describe(membro='Filtrar por membro (opcional)')
async def compras_listar(interaction: discord.Interaction, membro: str = None):
    await interaction.response.defer()
    try:
        resultado = await sheets_request({'aba': 'LerCompras', 'comprador': membro or ''})
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar compras: {e}', ephemeral=True)
        return

    if not resultado or not isinstance(resultado, list):
        msg = f'❌ Nenhuma compra encontrada para **{membro}**.' if membro else '❌ Nenhuma compra registrada ainda.'
        await interaction.followup.send(msg, ephemeral=True)
        return

    titulo = f'🛍️ Compras de {membro}' if membro else '🛍️ Histórico de Compras'
    embed = discord.Embed(title=titulo, color=0x9B59B6)

    for c in resultado[-10:]:  # últimas 10
        nome_campo = f"{c.get('item', '?')} ×{c.get('quantidade', '?')}"
        valor_campo = f"👤 {c.get('comprador', '?')}\n💵 R$ {c.get('valor', '?')}\n📅 {c.get('registrado_em', '?')}"
        if c.get('observacao') and c.get('observacao') != '-':
            valor_campo += f"\n📝 {c.get('observacao')}"
        embed.add_field(name=nome_campo, value=valor_campo, inline=False)

    embed.set_footer(text='Mostrando as últimas 10 compras')
    await interaction.followup.send(embed=embed)


# ── ANIVERSÁRIOS ──────────────────────────────────────────────────────────────

@tasks.loop(hours=4)
async def verificar_aniversarios():
    hoje = datetime.now().strftime('%d/%m')
    aniversarios = await sheets_get_aniversarios()
    for a in aniversarios:
        if a.get('data') != hoje:
            continue
        discord_id = str(a.get('discord_id', ''))
        if _aniversarios_enviados.get(discord_id) == hoje:
            continue
        for guild in bot.guilds:
            canal = discord.utils.get(guild.text_channels, name=CANAL_ANIVERSARIO)
            if not canal:
                continue
            membro = guild.get_member(int(discord_id))
            mencao = membro.mention if membro else a.get('nome', 'alguém')
            await canal.send(f'🎂🎉 Hoje é aniversário de {mencao}! Feliz aniversário! 🎊🥳')
        _aniversarios_enviados[discord_id] = hoje


@verificar_aniversarios.before_loop
async def before_verificar():
    await bot.wait_until_ready()


@bot.tree.command(name='aniversario', description='Cadastra o aniversário de um membro')
@discord.app_commands.describe(usuario='Membro do servidor', data='Data no formato DD/MM')
async def aniversario(interaction: discord.Interaction, usuario: discord.Member, data: str):
    await interaction.response.defer(ephemeral=True)
    if not re.match(r'^\d{2}/\d{2}$', data):
        await interaction.followup.send('❌ Formato de data inválido. Use DD/MM (ex: 25/12).', ephemeral=True)
        return
    dia, mes = int(data[:2]), int(data[3:])
    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        await interaction.followup.send('❌ Data inválida. Dia deve ser 01-31 e mês 01-12.', ephemeral=True)
        return
    try:
        await sheets_request({
            'aba': 'CadastrarAniversario',
            'nome': usuario.display_name,
            'discord_id': str(usuario.id),
            'data': data,
        })
        await interaction.followup.send(
            f'✅ Aniversário de **{usuario.display_name}** cadastrado para **{data}**!',
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao cadastrar aniversário: {e}', ephemeral=True)


# ── BOT ───────────────────────────────────────────────────────────────────────

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f'[ERRO COMANDO] {interaction.command.name if interaction.command else "?"}: {error}')
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(f'❌ Erro: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'❌ Erro: {error}', ephemeral=True)
    except Exception as e:
        print(f'[ERRO AO ENVIAR MENSAGEM DE ERRO] {e}')


@bot.event
async def on_ready():
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    synced = await bot.tree.sync()
    print(f'Bot conectado como {bot.user} | {len(synced)} comandos sincronizados em {len(bot.guilds)} servidor(es)')
    verificar_aniversarios.start()


async def health_check(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    await start_webserver()
    await bot.start(os.environ['DISCORD_TOKEN'])

asyncio.run(main())
