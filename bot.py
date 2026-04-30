import os
import re
import discord
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
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


async def sheets_get_precos() -> dict:
    result = await sheets_request({'aba': 'LerPrecos'})
    return result if isinstance(result, dict) else {}


async def sheets_get_encomendas(status: str = '') -> list:
    result = await sheets_request({'aba': 'LerEncomendas', 'status': status})
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


# ── PERÍMETROS ───────────────────────────────────────────────────────────────

LOJAS: dict[str, tuple[int, str]] = {
    'Vanilla':           (1,  'https://i.imgur.com/wqsv8Ly.jpeg'),
    'Rodovia Arcanjos':  (2,  'https://i.imgur.com/IuQLhOY.jpeg'),
    'Mirror Park':       (3,  'https://i.imgur.com/e9iEW0L.jpeg'),
    'China':             (4,  'https://i.imgur.com/cFmcVeo.jpeg'),
    'Guetos':            (5,  'https://i.imgur.com/snjrSC7.jpeg'),
    'Central':           (6,  'https://i.imgur.com/Vkw61vq.jpeg'),
    'Rodovia Praia':     (7,  'https://i.imgur.com/zz9txEG.jpeg'),
    'Paleto':            (8,  'https://i.imgur.com/o4jYeHM.jpeg'),
    'Rota 68 / Ark':     (9,  'https://i.imgur.com/hr7DUrk.jpeg'),
    'Sandy Shores':      (10, 'https://i.imgur.com/GmRTRJg.jpeg'),
    'Rodovia Presídio':  (11, 'https://i.imgur.com/rCCsh49.jpeg'),
    'Grapeseed':         (12, 'https://i.imgur.com/eH4fBKx.png'),
    'Naturalli':         (13, 'https://i.imgur.com/SzvaGkg.jpeg'),
}

ACOES: dict[str, str] = {
    'Açougue':                        'https://i.imgur.com/w39tZ4X.png',
    'Galinheiro':                     'https://i.imgur.com/kByVDF4.png',
    'Madeireira':                     'https://i.imgur.com/Jmlpf03.png',
    'Roubo à DP de Paleto':           'https://i.imgur.com/snXH0Zc.png',
    'Joalheria':                      'https://i.imgur.com/qKaiusy.png',
    'Fleeca - LifeInvader':           'https://i.imgur.com/9p6hybj.png',
    'Fleeca - Shopping':              'https://i.imgur.com/ZwGzhnl.png',
    'Fleeca - Rodovia Praia':         'https://i.imgur.com/4DSuduE.png',
    'Fleeca - Banco Paleto':          'https://i.imgur.com/jsoLKDg.png',
    'Fleeca - Vila do Chaves':        'https://i.imgur.com/A6s64PY.png',
    'Fleeca - Rota 68':               'https://i.imgur.com/Lt28YZT.png',
    'Banco Central':                  'https://i.imgur.com/dxG4MEF.png',
    'Transferência para Penitenciária': 'https://i.imgur.com/stFRtuQ.png',
    'Assalto ao Aeroporto do Norte':  'https://i.imgur.com/RGLERWY.png',
    'Assalto ao Ferro Velho (Sul)':   'https://i.imgur.com/RTofdQF.png',
    'Assalto ao Ferro Velho (Norte)': 'https://i.imgur.com/VKaegmS.png',
    'Plataforma de Petróleo':         'https://i.imgur.com/jBW9Mpn.png',
    'Assalto à Ilha':                 'https://i.imgur.com/JFsiwzS.png',
    'Blackout na Cidade':             'https://i.imgur.com/q6X9w2d.png',
    'Assalto ao Zancudo':             'https://i.imgur.com/Y2Mj0li.png',
}


async def perimetro_autocomplete(interaction: discord.Interaction, current: str) -> list:
    tipo = getattr(interaction.namespace, 'tipo', None)
    if tipo == 'loja':
        choices = [
            discord.app_commands.Choice(name=f'Loja {num} - {nome}', value=nome)
            for nome, (num, _) in LOJAS.items()
            if current.lower() in nome.lower()
        ]
    elif tipo == 'acao':
        choices = [
            discord.app_commands.Choice(name=nome, value=nome)
            for nome in ACOES
            if current.lower() in nome.lower()
        ]
    else:
        choices = [
            discord.app_commands.Choice(name=f'Loja {num} - {nome}', value=f'loja:{nome}')
            for nome, (num, _) in LOJAS.items()
            if current.lower() in nome.lower()
        ] + [
            discord.app_commands.Choice(name=f'Ação - {nome}', value=f'acao:{nome}')
            for nome in ACOES
            if current.lower() in nome.lower()
        ]
    return choices[:25]


@bot.tree.command(name='perimetro_lista', description='Lista todos os perímetros disponíveis')
async def perimetro_lista(interaction: discord.Interaction):
    lojas_txt = '\n'.join(f'`{num:02d}` {nome}' for nome, (num, _) in LOJAS.items())
    acoes_txt = '\n'.join(f'• {nome}' for nome in ACOES)

    embed = discord.Embed(title='📋 Perímetros Disponíveis', color=0x3498DB)
    embed.add_field(name='🏪 Lojas', value=lojas_txt, inline=True)
    embed.add_field(name='🔫 Ações Médias/Grandes', value=acoes_txt, inline=True)
    embed.set_footer(text='Use /perimetro para ver o mapa de cada um')
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='perimetro', description='Mostra o perímetro de uma loja ou ação média/grande')
@discord.app_commands.describe(tipo='Tipo de perímetro', nome='Nome da loja ou ação')
@discord.app_commands.choices(tipo=[
    discord.app_commands.Choice(name='Loja', value='loja'),
    discord.app_commands.Choice(name='Ação Média/Grande', value='acao'),
])
@discord.app_commands.autocomplete(nome=perimetro_autocomplete)
async def perimetro(interaction: discord.Interaction, tipo: str, nome: str):
    if tipo == 'loja':
        dados = LOJAS.get(nome)
        if not dados:
            await interaction.response.send_message('❌ Loja não encontrada.', ephemeral=True)
            return
        num, imagem = dados
        embed = discord.Embed(title=f'🏪 Loja {num} - {nome}', color=0xE74C3C)
    else:
        imagem = ACOES.get(nome)
        if not imagem:
            await interaction.response.send_message('❌ Ação não encontrada.', ephemeral=True)
            return
        embed = discord.Embed(title=f'🔫 {nome}', color=0xE67E22)

    embed.set_image(url=imagem)
    await interaction.response.send_message(embed=embed)


# ── COMPRAS ───────────────────────────────────────────────────────────────────

class CompraModal(discord.ui.Modal, title='Registro de Compra'):
    familia = discord.ui.TextInput(label='Família', placeholder='Ex: Nome da família/fornecedor', required=True)
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
                'familia': self.familia.value,
                'item': self.item.value,
                'quantidade': self.quantidade.value,
                'valor': self.valor.value,
                'observacao': self.observacao.value or '-',
                'registrado_em': registrado_em,
            })

            embed = discord.Embed(title='🛍️ Compra Registrada', color=0x9B59B6)
            embed.add_field(name='👤 Comprador', value=self.comprador, inline=True)
            embed.add_field(name='🏠 Família', value=self.familia.value, inline=True)
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


# ── VENDA DE MUNIÇÃO ─────────────────────────────────────────────────────────

MUNICAO_PRECOS: dict[str, float] = {
    'pistola': 90,
    'sub': 120,
    'fuzil': 165,
}

MUNICAO_MATERIAIS = {
    'pistola': {'dinheiro_sujo': 250, 'estojo': 'Estojo de Munição',            'polvora': 24},
    'sub':     {'dinheiro_sujo': 400, 'estojo': 'Estojo de Munição Automática', 'polvora': 30},
    'fuzil':   {'dinheiro_sujo': 500, 'estojo': 'Estojo de Munição Automática', 'polvora': 48},
}

MUNICAO_LABEL = {
    'pistola': 'Pistola',
    'sub':     'Sub',
    'fuzil':   'Fuzil',
}


def _parse_pagamento(raw: str) -> tuple[str, float, float]:
    """Parse pagamento field. Returns (tipo, perc_sujo, desconto).
    Accepts: 'limpo', 'sujo 30', 'limpo desc 10', 'sujo 30 desc 5'
    """
    parts = raw.strip().lower().split()
    if not parts or parts[0] not in ('limpo', 'sujo'):
        raise ValueError('tipo de pagamento inválido')
    tipo = parts[0]
    perc_sujo = 0.0
    desconto = 0.0
    i = 1
    while i < len(parts):
        if parts[i] == 'desc' and i + 1 < len(parts):
            desconto = float(parts[i + 1].replace(',', '.'))
            i += 2
        else:
            if tipo == 'sujo':
                perc_sujo = float(parts[i].replace(',', '.'))
            i += 1
    return tipo, perc_sujo, desconto


class VendaMunicaoMultiModal(discord.ui.Modal, title='Venda de Munição'):
    nome_comprador = discord.ui.TextInput(label='Nome do Comprador', placeholder='Ex: João Silva', required=True)
    qtd_pistola = discord.ui.TextInput(label='Qtd Pistola (0 para não incluir)', placeholder='0', default='0', required=False)
    qtd_sub = discord.ui.TextInput(label='Qtd Sub (0 para não incluir)', placeholder='0', default='0', required=False)
    qtd_fuzil = discord.ui.TextInput(label='Qtd Fuzil (0 para não incluir)', placeholder='0', default='0', required=False)
    pagamento_raw = discord.ui.TextInput(
        label='Pagamento',
        placeholder='limpo | sujo 30 | limpo desc 10 | sujo 30 desc 5',
        required=True,
    )

    def __init__(self, tipo_comprador: str, vendedor: str):
        super().__init__()
        self.tipo_comprador = tipo_comprador
        self.vendedor = vendedor

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            qtds = {
                'pistola': int((self.qtd_pistola.value or '0').strip() or '0'),
                'sub':     int((self.qtd_sub.value or '0').strip() or '0'),
                'fuzil':   int((self.qtd_fuzil.value or '0').strip() or '0'),
            }
        except ValueError:
            await interaction.followup.send('❌ Quantidades inválidas. Use apenas números inteiros.', ephemeral=True)
            return

        tipos_ativos = {t: q for t, q in qtds.items() if q > 0}
        if not tipos_ativos:
            await interaction.followup.send('❌ Informe quantidade maior que 0 em ao menos um tipo de munição.', ephemeral=True)
            return

        try:
            pag_tipo, perc_sujo, desconto = _parse_pagamento(self.pagamento_raw.value)
        except ValueError:
            await interaction.followup.send(
                '❌ Pagamento inválido. Use: `limpo`, `sujo 30`, `limpo desc 10`, `sujo 30 desc 5`.',
                ephemeral=True,
            )
            return

        try:
            registrado_em = datetime.now().strftime('%d/%m/%Y %H:%M')
            preco_total_geral = 0.0
            linhas_embed = []
            mat_totais: dict[str, float] = {}

            for tipo, qtd in tipos_ativos.items():
                preco_base = MUNICAO_PRECOS[tipo] * qtd
                preco_com_sujo = preco_base * (1 + perc_sujo / 100) if pag_tipo == 'sujo' else preco_base
                preco_final = preco_com_sujo * (1 - desconto / 100)
                crafts = -(-qtd // 250)
                mat = MUNICAO_MATERIAIS[tipo]

                chave_estojo = mat['estojo']
                mat_totais['dinheiro_sujo'] = mat_totais.get('dinheiro_sujo', 0) + mat['dinheiro_sujo'] * crafts
                mat_totais[chave_estojo] = mat_totais.get(chave_estojo, 0) + 250 * crafts
                mat_totais['polvora'] = mat_totais.get('polvora', 0) + mat['polvora'] * crafts

                preco_total_geral += preco_final
                linhas_embed.append(
                    f'**{MUNICAO_LABEL[tipo]}** — {qtd:,} unid. ({crafts} craft(s)) → R$ {preco_final:,.2f}'
                )

            await sheets_request({
                'aba': 'VendaMunicao',
                'nome_comprador': self.nome_comprador.value,
                'tipo_comprador': self.tipo_comprador,
                'pistola': qtds['pistola'],
                'sub': qtds['sub'],
                'fuzil': qtds['fuzil'],
                'pagamento': pag_tipo,
                'percentual_sujo': perc_sujo,
                'desconto': desconto,
                'preco_final': round(preco_total_geral, 2),
                'vendedor': self.vendedor,
                'registrado_em': registrado_em,
            })

            await sheets_request({
                'aba': 'CriarEncomenda',
                'vendedor': self.vendedor,
                'comprador': self.nome_comprador.value,
                'tipo_comprador': self.tipo_comprador,
                'pistola': qtds['pistola'],
                'sub': qtds['sub'],
                'fuzil': qtds['fuzil'],
                'total': round(preco_total_geral, 2),
                'registrado_em': registrado_em,
            })

            pag_txt = f'Sujo (+{perc_sujo:.0f}%)' if pag_tipo == 'sujo' else 'Limpo'
            if desconto > 0:
                pag_txt += f' • Desconto {desconto:.0f}%'

            embed = discord.Embed(title='🔫 Venda de Munição Registrada', color=0xE74C3C)
            embed.add_field(name='👤 Comprador', value=f'{self.nome_comprador.value} ({self.tipo_comprador})', inline=True)
            embed.add_field(name='🧑‍💼 Vendedor', value=self.vendedor, inline=True)
            embed.add_field(name='💳 Pagamento', value=pag_txt, inline=True)
            embed.add_field(name='📦 Munições', value='\n'.join(linhas_embed), inline=False)
            embed.add_field(name='💰 Total Geral', value=f'R$ {preco_total_geral:,.2f}', inline=False)

            mat_linhas = [f'💸 Dinheiro Sujo: {int(mat_totais.get("dinheiro_sujo", 0)):,}']
            for k, v in mat_totais.items():
                if k not in ('dinheiro_sujo', 'polvora'):
                    mat_linhas.append(f'📦 {k}: {int(v):,}')
            mat_linhas.append(f'💣 Pólvoras: {int(mat_totais.get("polvora", 0)):,}')
            embed.add_field(name='🔩 Materiais Consumidos', value='\n'.join(mat_linhas), inline=False)
            embed.set_footer(text=f'Registrado em {registrado_em} • Encomenda criada automaticamente')

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao registrar venda: {e}', ephemeral=True)


class CompradorTipoSelect(discord.ui.Select):
    def __init__(self, vendedor: str):
        self.vendedor_nome = vendedor
        options = [
            discord.SelectOption(label='CPF',      value='CPF'),
            discord.SelectOption(label='CNPJ',     value='CNPJ'),
            discord.SelectOption(label='Aliança',  value='Aliança'),
            discord.SelectOption(label='Parceria', value='Parceria'),
        ]
        super().__init__(placeholder='Selecione o tipo de comprador...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            VendaMunicaoMultiModal(self.values[0], self.vendedor_nome)
        )


class CompradorTipoView(discord.ui.View):
    def __init__(self, vendedor: str):
        super().__init__()
        self.add_item(CompradorTipoSelect(vendedor))


@bot.tree.command(name='venda_municao', description='Registra uma venda de munição (pistola, sub e/ou fuzil)')
async def venda_municao(interaction: discord.Interaction):
    vendedor = interaction.user.display_name
    embed = discord.Embed(title='🔫 Venda de Munição', description='Selecione o tipo de comprador:', color=0xE74C3C)
    await interaction.response.send_message(embed=embed, view=CompradorTipoView(vendedor), ephemeral=True)


@bot.tree.command(name='vendas_municao_listar', description='Lista o histórico de vendas de munição')
@discord.app_commands.describe(comprador='Filtrar por nome do comprador')
async def vendas_municao_listar(interaction: discord.Interaction, comprador: str = None):
    await interaction.response.defer()
    try:
        resultado = await sheets_request({
            'aba': 'LerVendaMunicao',
            'comprador': comprador or '',
        })
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar vendas: {e}', ephemeral=True)
        return

    if not resultado or not isinstance(resultado, list):
        msg = f'❌ Nenhuma venda encontrada para **{comprador}**.' if comprador else '❌ Nenhuma venda registrada ainda.'
        await interaction.followup.send(msg, ephemeral=True)
        return

    titulo = f'🔫 Vendas de Munição — {comprador}' if comprador else '🔫 Vendas de Munição'
    embed = discord.Embed(title=titulo, color=0xE74C3C)
    for v in resultado[-10:]:
        partes_qtd = []
        for t in ('pistola', 'sub', 'fuzil'):
            qtd = v.get(t, 0)
            try:
                qtd_int = int(qtd)
                if qtd_int > 0:
                    crafts_v = -(-qtd_int // 250)
                    partes_qtd.append(f'{MUNICAO_LABEL[t]}: {qtd_int:,} ({crafts_v}x craft)')
            except (ValueError, TypeError):
                pass
        nome_campo = ' | '.join(partes_qtd) if partes_qtd else '?'
        pag = v.get('pagamento', '?')
        perc = v.get('percentual_sujo', 0)
        desc = v.get('desconto', 0)
        pag_txt = f'Sujo (+{perc}%)' if pag == 'sujo' else 'Limpo'
        if desc:
            pag_txt += f' • Desc {desc}%'
        valor_campo = (
            f"👤 {v.get('nome_comprador', '?')} ({v.get('tipo_comprador', '?')})\n"
            f"💳 {pag_txt}\n"
            f"💰 R$ {v.get('preco_final', '?')}\n"
            f"🧑‍💼 {v.get('vendedor', '?')}\n"
            f"📅 {v.get('registrado_em', '?')}"
        )
        embed.add_field(name=nome_campo, value=valor_campo, inline=False)

    embed.set_footer(text='Mostrando as últimas 10 vendas')
    await interaction.followup.send(embed=embed)


# ── ENCOMENDAS ────────────────────────────────────────────────────────────────

class EntregaModal(discord.ui.Modal, title='Registrar Entrega'):
    qtd_pistola = discord.ui.TextInput(label='Qtd Pistola entregue', placeholder='0', default='0', required=False)
    qtd_sub = discord.ui.TextInput(label='Qtd Sub entregue', placeholder='0', default='0', required=False)
    qtd_fuzil = discord.ui.TextInput(label='Qtd Fuzil entregue', placeholder='0', default='0', required=False)
    observacao = discord.ui.TextInput(label='Observação (opcional)', placeholder='Ex: entrega parcial, falta de estoque', required=False)

    def __init__(self, encomenda_id: str, encomenda: dict):
        super().__init__()
        self.encomenda_id = encomenda_id
        self.comprador = encomenda.get('comprador', '?')
        self._restante = {
            'pistola': int(encomenda.get('pistola_total', 0)) - int(encomenda.get('pistola_entregue', 0)),
            'sub':     int(encomenda.get('sub_total',     0)) - int(encomenda.get('sub_entregue',     0)),
            'fuzil':   int(encomenda.get('fuzil_total',   0)) - int(encomenda.get('fuzil_entregue',   0)),
        }

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            qtd_p = int((self.qtd_pistola.value or '0').strip() or '0')
            qtd_s = int((self.qtd_sub.value or '0').strip() or '0')
            qtd_f = int((self.qtd_fuzil.value or '0').strip() or '0')
        except ValueError:
            await interaction.followup.send('❌ Quantidades inválidas.', ephemeral=True)
            return

        if qtd_p + qtd_s + qtd_f == 0:
            await interaction.followup.send('❌ Informe ao menos uma quantidade entregue.', ephemeral=True)
            return

        erros = []
        if qtd_p > self._restante['pistola']:
            erros.append(f'Pistola: informado {qtd_p:,}, restante {self._restante["pistola"]:,}')
        if qtd_s > self._restante['sub']:
            erros.append(f'Sub: informado {qtd_s:,}, restante {self._restante["sub"]:,}')
        if qtd_f > self._restante['fuzil']:
            erros.append(f'Fuzil: informado {qtd_f:,}, restante {self._restante["fuzil"]:,}')
        if erros:
            await interaction.followup.send(
                '❌ Quantidade informada supera o saldo da encomenda:\n' + '\n'.join(erros),
                ephemeral=True,
            )
            return

        try:
            registrado_em = datetime.now().strftime('%d/%m/%Y %H:%M')
            resultado = await sheets_request({
                'aba': 'RegistrarEntrega',
                'id': self.encomenda_id,
                'pistola': qtd_p,
                'sub': qtd_s,
                'fuzil': qtd_f,
                'obs': self.observacao.value or '',
                'registrado_em': registrado_em,
            })

            status_novo = resultado.get('status', '?') if isinstance(resultado, dict) else '?'
            embed = discord.Embed(title='📦 Entrega Registrada', color=0x2ECC71)
            embed.add_field(name='🆔 Encomenda', value=f'#{self.encomenda_id}', inline=True)
            embed.add_field(name='👤 Comprador', value=self.comprador, inline=True)
            embed.add_field(name='📊 Status', value=status_novo, inline=True)
            partes = []
            if qtd_p: partes.append(f'Pistola: {qtd_p:,}')
            if qtd_s: partes.append(f'Sub: {qtd_s:,}')
            if qtd_f: partes.append(f'Fuzil: {qtd_f:,}')
            embed.add_field(name='📦 Entregue agora', value='\n'.join(partes), inline=False)
            if self.observacao.value:
                embed.add_field(name='📝 Observação', value=self.observacao.value, inline=False)
            embed.set_footer(text=f'Registrado em {registrado_em} • por {interaction.user.display_name}')
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao registrar entrega: {e}', ephemeral=True)


class EncomendaSelect(discord.ui.Select):
    def __init__(self, encomendas: list):
        self._encomendas_map = {str(e.get('id')): e for e in encomendas}
        options = []
        for e in encomendas[:25]:
            eid = str(e.get('id', '?'))
            comprador = e.get('comprador', '?')
            status = e.get('status', '?')
            partes = []
            for t in ('pistola', 'sub', 'fuzil'):
                total = e.get(f'{t}_total', 0)
                entregue = e.get(f'{t}_entregue', 0)
                if total:
                    partes.append(f'{MUNICAO_LABEL[t]}: {entregue}/{total}')
            desc = ', '.join(partes) if partes else '—'
            options.append(discord.SelectOption(
                label=f'#{eid} — {comprador} ({status})'[:100],
                value=eid,
                description=desc[:100],
            ))
        super().__init__(placeholder='Selecione a encomenda...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        eid = self.values[0]
        enc = self._encomendas_map.get(eid, {})
        await interaction.response.send_modal(EntregaModal(eid, enc))


class EncomendaView(discord.ui.View):
    def __init__(self, encomendas: list):
        super().__init__()
        self.add_item(EncomendaSelect(encomendas))


@bot.tree.command(name='encomenda_listar', description='Lista encomendas de munição e seus status de entrega')
@discord.app_commands.describe(status='Filtrar por status (padrão: encomendas abertas)')
@discord.app_commands.choices(status=[
    discord.app_commands.Choice(name='Pendente', value='Pendente'),
    discord.app_commands.Choice(name='Parcial',  value='Parcial'),
    discord.app_commands.Choice(name='Completa', value='Completa'),
    discord.app_commands.Choice(name='Todas',    value='todas'),
])
async def encomenda_listar(interaction: discord.Interaction, status: str = 'abertas'):
    await interaction.response.defer()
    try:
        encomendas = await sheets_get_encomendas(status)
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar encomendas: {e}', ephemeral=True)
        return

    if not encomendas:
        await interaction.followup.send('❌ Nenhuma encomenda encontrada.', ephemeral=True)
        return

    status_titulo = status.capitalize() if status not in ('abertas', 'todas') else ('Abertas' if status == 'abertas' else 'Todas')
    embed = discord.Embed(title=f'📦 Encomendas — {status_titulo}', color=0x3498DB)
    for e in encomendas[-10:]:
        eid = e.get('id', '?')
        comprador = e.get('comprador', '?')
        tipo_c = e.get('tipo_comprador', '?')
        vendedor = e.get('vendedor', '?')
        st = e.get('status', '?')
        data = e.get('registrado_em', '?')
        partes = []
        for t in ('pistola', 'sub', 'fuzil'):
            total = e.get(f'{t}_total', 0)
            entregue = e.get(f'{t}_entregue', 0)
            if total:
                partes.append(f'{MUNICAO_LABEL[t]}: {entregue:,}/{total:,}')
        nome_campo = f'#{eid} — {comprador} ({tipo_c}) • {st}'
        valor_campo = f"🧑‍💼 {vendedor}\n📦 {' | '.join(partes) if partes else '—'}\n📅 {data}"
        embed.add_field(name=nome_campo, value=valor_campo, inline=False)

    embed.set_footer(text='Mostrando as últimas 10 encomendas')
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='encomenda_entregar', description='Registra entrega (parcial ou completa) de uma encomenda')
async def encomenda_entregar(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        encomendas = await sheets_get_encomendas('abertas')
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao buscar encomendas: {e}', ephemeral=True)
        return

    if not encomendas:
        await interaction.followup.send('✅ Nenhuma encomenda aberta no momento.', ephemeral=True)
        return

    await interaction.followup.send(
        'Selecione a encomenda para registrar a entrega:',
        view=EncomendaView(encomendas),
        ephemeral=True,
    )


# ── PREÇO DE MUNIÇÃO ──────────────────────────────────────────────────────────

class PrecoModal(discord.ui.Modal, title='Alterar Preço de Munição'):
    novo_preco = discord.ui.TextInput(label='Novo Preço (R$ por unidade)', placeholder='Ex: 100', required=True)

    def __init__(self, tipo: str):
        super().__init__()
        self.tipo = tipo

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            preco = float(self.novo_preco.value.replace(',', '.'))
            if preco <= 0:
                await interaction.followup.send('❌ O preço deve ser maior que zero.', ephemeral=True)
                return
            MUNICAO_PRECOS[self.tipo] = preco
            await sheets_request({'aba': 'AtualizarPreco', 'tipo': self.tipo, 'preco': preco})
            await interaction.followup.send(
                f'✅ Preço de **{MUNICAO_LABEL[self.tipo]}** atualizado para **R$ {preco:,.2f}** por unidade.',
                ephemeral=True,
            )
        except ValueError:
            await interaction.followup.send('❌ Valor inválido. Use apenas números (ex: 100 ou 99,50).', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Erro ao atualizar preço: {e}', ephemeral=True)


class PrecoTipoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f'Pistola (R$ {MUNICAO_PRECOS["pistola"]:,.0f}/unid)', value='pistola'),
            discord.SelectOption(label=f'Sub (R$ {MUNICAO_PRECOS["sub"]:,.0f}/unid)',     value='sub'),
            discord.SelectOption(label=f'Fuzil (R$ {MUNICAO_PRECOS["fuzil"]:,.0f}/unid)', value='fuzil'),
        ]
        super().__init__(placeholder='Selecione o tipo de munição...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PrecoModal(self.values[0]))


class PrecoTipoView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PrecoTipoSelect())


@bot.tree.command(name='preco', description='Altera o preço de venda de um tipo de munição')
async def preco(interaction: discord.Interaction):
    embed = discord.Embed(
        title='💲 Alterar Preço de Munição',
        description=(
            f'**Pistola:** R$ {MUNICAO_PRECOS["pistola"]:,.2f}/unid\n'
            f'**Sub:** R$ {MUNICAO_PRECOS["sub"]:,.2f}/unid\n'
            f'**Fuzil:** R$ {MUNICAO_PRECOS["fuzil"]:,.2f}/unid'
        ),
        color=0xF1C40F,
    )
    await interaction.response.send_message(embed=embed, view=PrecoTipoView(), ephemeral=True)


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
    try:
        precos = await sheets_get_precos()
        MUNICAO_PRECOS.update(precos)
        print(f'Preços carregados do Sheets: {MUNICAO_PRECOS}')
    except Exception as e:
        print(f'Aviso: não foi possível carregar preços do Sheets: {e}')
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
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_TOKEN não encontrado. Verifique o arquivo .env')
    await start_webserver()
    await bot.start(token)

asyncio.run(main())
