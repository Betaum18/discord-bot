import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.command(name='lavar')
async def lavar(ctx, valor_sujo: float, margem_venda: float, margem_maquina: float):
    """
    Uso: !lavar <valor_sujo> <margem_venda%> <margem_maquina%>
    Exemplo: !lavar 10000 30 10
    """
    taxa_cobrada = valor_sujo * (margem_venda / 100)
    custo_maquina = valor_sujo * (margem_maquina / 100)
    lucro = taxa_cobrada - custo_maquina
    valor_limpo = valor_sujo - taxa_cobrada

    embed = discord.Embed(title="🧼 Cálculo de Lavagem", color=0x2ecc71)
    embed.add_field(name="💵 Valor Sujo", value=f"R$ {valor_sujo:,.2f}", inline=False)
    embed.add_field(name="📤 Taxa Cobrada do Cliente", value=f"R$ {taxa_cobrada:,.2f} ({margem_venda}%)", inline=True)
    embed.add_field(name="⚙️ Custo da Máquina", value=f"R$ {custo_maquina:,.2f} ({margem_maquina}%)", inline=True)
    embed.add_field(name="✅ Valor Limpo (cliente recebe)", value=f"R$ {valor_limpo:,.2f}", inline=False)
    embed.add_field(name="💰 Seu Lucro", value=f"R$ {lucro:,.2f} ({margem_venda - margem_maquina:.0f}%)", inline=False)

    await ctx.send(embed=embed)

@lavar.error
async def lavar_error(ctx, error):
    await ctx.send("❌ Uso correto: `!lavar <valor> <margem_venda%> <margem_maquina%>`\nExemplo: `!lavar 10000 30 10`")

bot.run(os.environ['DISCORD_TOKEN'])
