from datetime import datetime

from core import Asteroid, Language
from interactions import (
    Choice,
    CommandContext,
    EmbedField,
    Extension,
    Modal,
    TextInput,
    TextStyleType,
)
from interactions import extension_command as command
from interactions import extension_listener as listener
from interactions import extension_modal as modal
from interactions import option

from core import Locale, TimeStampsMentions, Mentions  # isort: skip
from utils import create_embed  # isort: skip


def build_modal(
    locale: Locale,
    is_embed: bool = True,
    *,
    name: str = None,
    title: str = None,
    description: str = None,
    custom_id: str = None,
) -> Modal:
    components = [
        TextInput(
            label=locale["MODAL_TAG_NAME"],
            custom_id="name",
            placeholder="The cool tag",
            required=True,
            style=TextStyleType.SHORT,
            value=name,
        ),
        TextInput(
            label=locale["MODAL_TAG_CONTENT"],
            custom_id="content",
            placeholder="There is a way to apply for moderator",
            required=True,
            style=TextStyleType.PARAGRAPH,
            value=description,
        ),
    ]
    if is_embed:
        components.insert(
            1,
            TextInput(
                label=locale["MODAL_TAG_TITLE"],
                custom_id="title",
                placeholder="Apply for moderator",
                required=True,
                style=TextStyleType.SHORT,
                value=title,
            ),
        )

    return Modal(
        title=locale["MODAL_CREATE_TAG"],
        custom_id=custom_id or "modal_create_tag",
        components=components,
    )


class Misc(Extension):
    def __init__(self, client: Asteroid):
        self.client: Asteroid = client

    @command()
    @option(
        description="The language to change",
        choices=[Choice(name=lang.name.lower().capitalize(), value=lang.value) for lang in Language],  # type: ignore
    )
    async def language(self, ctx: CommandContext, language: str):
        """Change language for bot on this server"""
        await ctx.defer(ephemeral=True)

        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        guild_data.settings.language = language
        await guild_data.settings.update()

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(description=locale["LANGUAGE_CHANGED"])
        await ctx.send(embeds=embed)

    @command()
    async def tag(self, ctx: CommandContext):
        ...

    @tag.autocomplete("name")
    async def tag_autocomplete(self, ctx: CommandContext):
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        choices = [Choice(name=tag.name, value=tag.name) for tag in guild_data.tags]
        await ctx.populate(choices)

    @tag.subcommand(name="view")
    @option(description="The name of tag to view", autocomplete=True)
    async def tag_view(self, ctx: CommandContext, name: str):
        """View a tag"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        tag = guild_data.get_tag(name)
        if tag is None:
            raise  # TODO: Exception
        if tag.is_embed:
            await ctx.send(embeds=create_embed(description=tag.description, title=tag.title))
        else:
            await ctx.send(tag.description)

        tag.uses_count += 1
        await tag.update()

    @tag.subcommand(name="create")
    @option(
        description="The type of tag",
        choices=[Choice(name=i, value=i.lower()) for i in ["Embed", "Simple"]],
    )
    async def tag_create(self, ctx: CommandContext, type: str):
        """Create a tag"""
        locale = await self.client.get_locale(ctx.guild_id)
        await ctx.popup(build_modal(locale, type == "embed"))

    @modal("modal_create_tag")
    async def modal_create_tag(
        self, ctx: CommandContext, name: str, title: str, content: str = None
    ):
        await ctx.defer(ephemeral=True)

        if content is None:
            title, content = content, title

        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        await guild_data.add_tag(
            name=name,
            title=title,
            description=content,
            author_id=int(ctx.author.id),
            is_embed=title is not None,
            created_at=int(datetime.utcnow().timestamp()),
            last_edited_at=None,
            uses_count=0,
        )
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["TAG_CREATED"].format(name=name))
        await ctx.send(embeds=embed)

    @tag.subcommand(name="delete")
    @option(description="The name of tag to delete", autocomplete=True)
    async def tag_delete(self, ctx: CommandContext, name: str):
        """Delete a tag"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        await guild_data.remove_tag(name)

    @tag.subcommand(name="edit")
    @option(description="The name of tag to edit", autocomplete=True)
    async def tag_edit(self, ctx: CommandContext, name: str):
        """Edit a tag"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        tag = guild_data.get_tag(name)
        if tag is None:
            raise  # TODO: Exception
        locale = await self.client.get_locale(int(ctx.guild_id))

        await ctx.popup(
            build_modal(
                locale,
                is_embed=tag.is_embed,
                name=tag.name,
                title=tag.title,
                description=tag.description,
                custom_id=f"modal_edit_tag|{tag.name}",  # We should store current name of tag because we can change it
            )
        )

    @listener
    async def on_modal(self, ctx: CommandContext):
        def get_value(ind: int):
            return ctx.data.components[ind].components[0].value

        if not ctx.data.custom_id.startswith("modal_edit_tag"):
            return

        await ctx.defer(ephemeral=True)
        name = get_value(0)
        if len(ctx.data.components) == 3:
            title = get_value(1)
            description = get_value(2)
        else:
            description = get_value(1)

        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        tag = guild_data.get_tag(ctx.data.custom_id.split("|")[1])
        tag.name = name
        tag.title = title
        tag.description = description
        tag.last_edited_at = int(datetime.utcnow().timestamp())
        await tag.update()

        await ctx.send("Tag edited!")  # TODO: Locale

    @tag.subcommand(name="list")
    async def tag_list(self, ctx: CommandContext):
        """Show list of tags"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        description = "\n".join(
            [f"**{ind}.** `{tag.name}`" for ind, tag in enumerate(guild_data.tags, start=1)]
        )
        await ctx.send(
            embeds=create_embed(description=description, title="List of tags")
        )  # TODO: Locale

    @tag.subcommand(name="info")
    @option(description="The name of tag to view", autocomplete=True)
    async def tag_info(self, ctx: CommandContext, name: str):
        """Show information about tag"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        tag = guild_data.get_tag(name)
        if tag is None:
            raise  # TODO: Exception

        def get_timestamp_string(timestamp: int):
            return f"{TimeStampsMentions.LONG.format(timestamp=timestamp)} ({TimeStampsMentions.RELATIVE.format(timestamp=timestamp)})"

        # TODO: Locale
        fields = [
            EmbedField(name="Author", value=Mentions.USER.format(id=tag.author_id), inline=True),
            EmbedField(name="Uses count", value=f"`{tag.uses_count}`", inline=True),
            EmbedField(
                name="Timestamps",
                value=f"**Created at** {get_timestamp_string(tag.created_at)}\n"
                + (
                    f"**Last edited at** {get_timestamp_string(tag.last_edited_at)}"
                    if tag.last_edited_at is not None
                    else ""
                ),
                inline=True,
            ),
        ]
        embed = create_embed(title=tag.name, fields=fields)
        await ctx.send(embeds=embed)


def setup(client):
    Misc(client)
