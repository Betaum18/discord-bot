import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


class LavagemModal(discord.ui.Modal, title='Cálculo de Lavagem'):
    nome = discord.ui.TextInput(
        label='Nome',
        placeholder='Ex: João Silva',
        required=True
    )
    valor_sujo = discord.ui.TextInput(
        label='Valor Sujo',
        placeholder='Ex: 10000',
        required=True
    )
    margem_venda = discord.ui.TextInput(
        label='Taxa Cobrada do Cliente (%)',
        placeholder='Ex: 30',
        required=True
    )
    margem_maquina = discord.ui.TextInput(
        label='Custo da Máquina (%)',
        placeholder='Ex: 10',
        required=True
    )

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

            embed = discord.Embed(title="🧼 Cálculo de Lavagem", color=0x2ecc71)
            embed.add_field(name="👤 Nome", value=nome, inline=False)
            embed.add_field(name="💵 Valor Sujo", value=f"R$ {valor_sujo:,.2f}", inline=False)
            embed.add_field(name="📤 Taxa Cobrada do Cliente", value=f"R$ {taxa_cobrada:,.2f} ({margem_venda}%)", inline=True)
            embed.add_field(name="⚙️ Custo da Máquina", value=f"R$ {custo_maquina:,.2f} ({margem_maquina}%)", inline=True)
            embed.add_field(name="✅ Valor Limpo (cliente recebe)", value=f"R$ {valor_limpo:,.2f}", inline=False)
            embed.add_field(name="💰 Seu Lucro", value=f"R$ {lucro:,.2f} ({margem_venda - margem_maquina:.0f}%)", inline=False)

            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "❌ Valores inválidos. Use apenas números nos campos de valor e porcentagem.",
                ephemeral=True
            )


@bot.tree.command(name='lavagem', description='Abre o formulário de cálculo de lavagem')
async def lavagem(interaction: discord.Interaction):
    await interaction.response.send_modal(LavagemModal())


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot conectado como {bot.user}')


bot.run(os.environ['DISCORD_TOKEN'])
