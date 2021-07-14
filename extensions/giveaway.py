from asyncio import sleep
from random import choice
from time import time

import discord
from discord.ext import commands
from discord_components import Button, ButtonStyle
from discord_components.interaction import Interaction

from extensions.bot_settings import get_embed_color, DurationConverter, multiplier
from ._levels import update_member



class Giveaway(commands.Cog, description='Розыгрыши'):
    def __init__(self, bot):
        self.bot = bot
        self.hidden = False

        self.members = {}


    @commands.group(
        name='giveaway',
        aliases=['ga'],
        description='Основная команда для розыгрышей',
        help='[команда]',
        invoke_without_command=True)
    async def giveaway(self, ctx:commands.Context):
        await ctx.send('Тут пока пусто. :(')


    @giveaway.command(
        name='role',
        description='Выдаёт роль рандомному участнику после установленного времени',
        help='[время] [роль] [сообщение]',
        usage='Только для Администрации')
    @commands.has_guild_permissions(administrator=True)
    async def role(self, ctx:commands.Context, duration:DurationConverter, role:discord.Role, *, message):
        msg = await self.create_message(ctx, 'Розыгрыш Роли', duration, message)
        await self.process_giveaway(ctx, duration, msg, 'role', role=role)


    @giveaway.command(
        name='xp',
        description='Выдаёт опыт рандомному участнику после установленного времени',
        help='[время] [опыт] [сообщение]',
        usage='Только для Администрации')
    @commands.has_guild_permissions(administrator=True)
    async def xp(self, ctx:commands.Context, duration:DurationConverter, exp:int, *, message):
        msg = await self.create_message(ctx, 'Розыгрыш Опыта', duration, message)
        await self.process_giveaway(ctx, duration, msg, 'exp', exp=exp)


    @giveaway.command(
        name='thing',
        description='Выдаёт символическую вещь рандомному участнику после установленного времени',
        help='[время] ["вещь"] [сообщение]')
    async def thing(self, ctx:commands.Context, duration:DurationConverter, thing:str, *, message):
        msg = await self.create_message(ctx, 'Розыгрыш', duration, message)
        await self.process_giveaway(ctx, duration, msg, 'thing', thing=thing)


    @giveaway.command(
        name='random',
        description='Рандомно выбирает 1 участника после установленного времени',
        help='[время] [сообщение]')
    async def random(self, ctx:commands.Context, duration:DurationConverter, *, message):
        msg = await self.create_message(ctx, 'Рандомный пользователь', duration, message)
        await self.process_giveaway(ctx, duration, msg, 'other')


    async def create_message(self, ctx:commands.Context, mode, duration:DurationConverter, message:discord.Message):
        amount, time_format = duration
        timestamp = amount * multiplier[time_format]
        embed = discord.Embed(title=mode)
        embed.description = f"""
        Заканчивается через <t:{int(time() + timestamp)}:R>
        {message}
        """
        await ctx.message.delete()
        components = [
            Button(style=ButtonStyle.green, label='Принять участие', id='giveaway_accept')
        ]

        return await ctx.send(embed=embed, components=components)


    async def process_giveaway(self, ctx, duration, message:discord.Message, mode, *, role:discord.Role=None, exp:int=None, thing:str=None):
        amount, time_format = duration
        guild_id = str(ctx.guild.id)
        message_id = str(message.id)

        await sleep(amount * multiplier[time_format])
        winner = choice(self.members[guild_id][message_id])
        member = await ctx.guild.fetch_member(winner)

        embed = discord.Embed(title='ИТОГИ РОЗЫГРЫША', color=get_embed_color(ctx.guild.id))

        if mode == 'role':
            await member.add_roles(role)
            embed.description = f'Победитель, {member.mention}! Вы получаете роль: `{role}`'
        elif mode == 'exp':
            await update_member(member, exp)
            embed.description =f'Победитель, {member.mention}! Вы получаете `{exp}` опыта'
        elif mode == 'thing':
            embed.description =f'Победитель, {member.mention}! Вы получаете {thing}'
        else:
            embed.description =f'Победитель, {member.mention}!'

        await ctx.send(embed=embed)
        await message.delete()
        del self.members[guild_id][message_id]
    

    @commands.Cog.listener()
    async def on_button_click(self, interaction:Interaction):
        if interaction.component.id != 'giveaway_accept':
            return
        guild = str(interaction.guild.id)
        message = str(interaction.message.id)
        user = interaction.user.id

        if guild not in self.members:
            self.members[guild] = {}
        if message not in self.members[guild]:
            self.members[guild][message] = []

        try:
            if not interaction.responded:
                if user in self.members[guild][message]:
                    await interaction.respond(type=4, content='Вы уже приняли участие в этой раздаче!')
                else:
                    await interaction.respond(type=4, content='Вы приняли участие!')
                    self.members[guild][message].append(user)
        except Exception:
            pass



def setup(bot):
    bot.add_cog(Giveaway(bot))