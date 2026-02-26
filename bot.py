import os
import discord
from discord.ext import commands
from datetime import datetime
import aiohttp
import json

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbw2tywG42XA7R8bFq_XPF-S2QjU5eTKpDBa59KnNukWfpPOXU3UJIR-emVvMZURuK0O/exec'


async def sheets_post(payload: dict):
    async with aiohttp.ClientSession() as session:
        # Google Apps Script redireciona o POST para GET — seguimos o redirect mantendo POST
        async with session.post(APPS_SCRIPT_URL, json=payload, allow_redirects=False) as resp:
            if resp.status in (301, 302, 303, 307, 308):
                redirect_url = resp.headers['Location']
                async with session.post(redirect_url, json=payload) as resp2:
                    text = await resp2.text()
                    print(f'sheets_post resposta: {text}')
                    return
            text = await resp.text()
            print(f'sheets_post resposta: {text}')


async def sheets_get_vendedores() -> list:
    async with aiohttp.ClientSession() as session:
        async with session.post(APPS_SCRIPT_URL, json={"aba": "LerVendedores"}, allow_redirects=False) as resp:
            if resp.status in (301, 302, 303, 307, 308):
                redirect_url = resp.headers['Location']
                async with session.post(redirect_url, json={"aba": "LerVendedores"}) as resp2:
                    return await resp2.json(content_type=None)
            return await resp.json(content_type=None)


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
            await sheets_post({
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

        await sheets_post({
            'aba': 'Vendedores',
            'nome': nome,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
        })
        await interaction.followup.send(f'✅ Vendedor **{nome}** cadastrado com sucesso!', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'❌ Erro ao cadastrar vendedor: {e}', ephemeral=True)


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
    synced = await bot.tree.sync()
    print(f'Bot conectado como {bot.user} | {len(synced)} comandos sincronizados')


bot.run(os.environ['DISCORD_TOKEN'])
