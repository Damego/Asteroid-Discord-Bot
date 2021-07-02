import discord
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle
import DiscordUtils

from extensions.bot_settings import get_embed_color, get_db


class NotConnectedToVoice(commands.CommandError):
    pass


class NewMusic(commands.Cog, description='Музыка с плеером'):
    def __init__(self, bot):
        self.bot = bot
        self.hidden = False
        self.music = DiscordUtils.Music()

        self.track_dict = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        player = self.music.get_player(guild_id=member.guild.id)
        print('after channel', after.channel)
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                try:
                    await self.msg.channel.send('**Бот отключился, из-за отсутствия слушателей!**', delete_after=10)
                    await player.stop()
                    await self.voice_client.disconnect()
                    await self.msg.edit(components=[])
                except:
                    pass
                
        elif member.bot and after.channel is None:
            await player.stop()
            print('vc b',self.voice_client)
            await self.voice_client.disconnect()
            print('vc a',self.voice_client)
            await self.msg.edit(components=[])
            

    async def wait_button_click(self, ctx, msg):
        async def check(interaction):
            member_converter = commands.MemberConverter()
            member = await member_converter.convert(ctx, interaction.user.name)
            
            if ('move_members', True) in member.guild_permissions:
                return True
            else:
                try:
                    members_in_channel = member.voice.channel.members
                except Exception:
                    pass
                for channel_member in members_in_channel:
                    if channel_member.bot:
                        return True

        while True:
            interaction = await self.bot.wait_for("button_click")
            is_in_channel = await check(interaction)
            if not is_in_channel:
                await interaction.interactionpond(type=5, content='Подключитесь к каналу, для управления музыкой')
            else:
                await interaction.interactionpond(type=6)
                id = interaction.component.id
                
                try:
                    if id == '1':
                        await self.new_pause_music(ctx, msg)
                    elif id == '2':
                        await self.new_stop_music(ctx, msg)
                        return
                    elif id == '3':
                        await self.new_skip_music(ctx, msg)
                    elif id == '4':
                        await self.new_resume_music(ctx, msg)
                    elif id == '5':
                        await self.new_repeat_music(ctx, msg)
                except Exception as e:
                    print(e)

    async def send_msg(self, ctx, track):
        duration = track.duration
        if duration != 0.0:
            duration_hours = duration // 3600
            duration_minutes = (duration // 60) % 60
            duration_seconds = duration % 60
            duration = f'{duration_hours:02}:{duration_minutes:02}:{duration_seconds:02}'
        else:
            duration = 'Прямая трансляция'

        embed = discord.Embed(title='Запуск музыки',
                              color=get_embed_color(ctx.message))
        embed.add_field(name='Название:',
                        value=f'[{track.name}]({track.url})', inline=False)
        embed.add_field(name='Продолжительность:',
                        value=duration, inline=False)
        embed.set_footer(text=f'Добавлено: {ctx.message.author}', icon_url=ctx.message.author.avatar_url)
        embed.set_thumbnail(url=track.thumbnail)

        self.components = [[
            Button(style=ButtonStyle.gray, label='Пауза', id=1),
            Button(style=ButtonStyle.red, label='Стоп', id=2),
            Button(style=ButtonStyle.blue, label='Пропустить', id=3),
            Button(style=ButtonStyle.blue, label='Вкл. повтор', id=5)
        ]]

        msg = await ctx.send(embed=embed, components=self.components)
        self.msg = msg
        return msg

    async def update_msg(self, ctx, msg, track):
        music_requester = self.track_dict.get(track.name)["requester_msg"]
        music_requester_avatar = music_requester.avatar_url
        duration = track.duration
        if duration != 0.0:
            duration_hours = duration // 3600
            duration_minutes = (duration // 60) % 60
            duration_seconds = duration % 60
            duration = f'{duration_hours:02}:{duration_minutes:02}:{duration_seconds:02}'
        else:
            duration = 'Прямая трансляция'

        embed = discord.Embed(title='Запуск музыки',
                              color=get_embed_color(ctx.message))
        embed.add_field(name='Название:',
                        value=f'[{track.name}]({track.url})', inline=False)
        embed.add_field(name='Продолжительность:',
                        value=duration, inline=False)
        embed.set_footer(text=f'Добавлено: {music_requester}', icon_url=music_requester_avatar)
        embed.set_thumbnail(url=track.thumbnail)

        await msg.edit(embed=embed)

    @commands.command(name='nplay', description='Запускает музыку', help='[ссылка || название видео]')
    async def new_play_music(self, ctx, *, query):
        if not ctx.message.author.voice:
            raise NotConnectedToVoice
        

        voice_channel = ctx.author.voice.channel

        print(ctx.voice_client)
        if not ctx.voice_client is None:
             if not ctx.voice_client.is_playing():
                print('disconnect')
                try:
                    await ctx.voice_client.stop()
                except Exception as e:
                    print('discnn', e)
                    try:
                        await ctx.voice_client.disconnect()
                    except Exception as e:
                        print('in try try', e)


        print('after discnn',ctx.voice_client)
        try:
            print('is conn', ctx.voice_client.is_connected())

            if not ctx.voice_client.is_connected():
                await voice_channel.connect()
        except Exception as e:
            print(e)


        if not ctx.voice_client:
            await voice_channel.connect()
            self.voice_client = ctx.voice_client
        print(ctx.voice_client)

        player = self.music.get_player(guild_id=ctx.guild.id)
        if player is None:
            player = self.music.create_player(ctx, ffmpeg_error_betterfix=True)

        track = await player.queue(query, search=True)
        await ctx.message.delete()
        if not ctx.voice_client.is_playing():
            await player.play()
            msg = await self.send_msg(ctx, track)
            await self.wait_button_click(ctx, msg)
        else:
            await ctx.send(f"`{track.name}` был добавлен в очередь")
            self.track_dict[track.name] = {'track': track, 'requester_msg': ctx.author}

    async def new_stop_music(self, ctx, msg):
        player = self.music.get_player(guild_id=ctx.guild.id)
        if ctx.voice_client.is_playing():
            await player.stop()
            await ctx.voice_client.disconnect()
        return await msg.edit(components=[])

    async def new_pause_music(self, ctx, msg):
        player = self.music.get_player(guild_id=ctx.guild.id)
        if ctx.voice_client.is_playing():
            await player.pause()
            try:
                self.components[0][0] = Button(
                    style=ButtonStyle.green, label='Продолжить', id=4)
                await msg.edit(components=self.components)
            except Exception as e:
                print('IN PAUSE', e)
        else:
            embed = discord.Embed(
                title='Музыка не воспроизводится!', color=get_embed_color(ctx.message))
            await ctx.send(embed=embed, delete_after=10)

    async def new_resume_music(self, ctx, msg):
        player = self.music.get_player(guild_id=ctx.guild.id)
        if not ctx.voice_client.is_playing():
            await player.resume()
            self.components[0][0] = Button(
                style=ButtonStyle.gray, label='Пауза', id=1)
            await msg.edit(components=self.components)

    async def new_repeat_music(self, ctx, msg):
        player = self.music.get_player(guild_id=ctx.guild.id)
        song = await player.toggle_song_loop()
        if song.is_looping:
            self.components[0][3] = Button(
                style=ButtonStyle.blue, label='Выкл. повтор', id=5)
        else:
            self.components[0][3] = Button(
                style=ButtonStyle.blue, label='Вкл. повтор', id=5)
        await msg.edit(components=self.components)

    async def new_skip_music(self, ctx, msg):
        player = self.music.get_player(guild_id=ctx.guild.id)
        try:
            old_track, new_track = await player.skip(force=True)
            await self.update_msg(ctx, msg, new_track)
        except TypeError:
            await ctx.send('**Плейлист пуст! Добавьте музыку!**', delete_after=15)

    # ERRORS
    @new_play_music.error
    async def play_music_error(self, ctx, error):
        if isinstance(error, NotConnectedToVoice):
            await ctx.send('Вы не подключены к голосовому чату!')


def setup(bot):
    DiscordComponents(bot)
    bot.add_cog(NewMusic(bot))
