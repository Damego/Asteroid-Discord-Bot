from discord import Role, Embed, RawReactionActionEvent, Guild, Member
from discord_slash import AutoCompleteContext, SlashContext, SlashCommandOptionType
from discord_slash.cog_ext import cog_subcommand as slash_subcommand
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_components import Select, SelectOption, Button, ButtonStyle
from discord_slash_components_bridge import ComponentContext, ComponentMessage
from pymongo.collection import Collection

from my_utils import (
    AsteroidBot,
    get_content,
    Cog,
    bot_owner_or_permissions,
    is_enabled,
    _cog_is_enabled,
    CogDisabledOnGuild,
    consts,
)


class AutoRole(Cog):
    def __init__(self, bot: AsteroidBot):
        self.bot = bot
        self.name = "AutoRole"
        self.emoji = "✨"

    # ON JOIN ROLE
    @Cog.listener()
    async def on_member_join(self, member: Member):
        if member.bot:
            return

        collection = self.bot.get_guild_main_collection(member.guild.id)
        config = collection.find_one({"_id": "configuration"})
        on_join_roles = config.get("on_join_roles")
        if on_join_roles is None:
            return
        guild = member.guild
        for role_id in on_join_roles:
            role: Role = guild.get_role(role_id)
            await member.add_roles(role)

    @Cog.listener(name="on_autocomplete")
    async def autorole_select_autocomplete(self, ctx: AutoCompleteContext):
        command_name = self.bot.get_transformed_command_name(ctx)
        if not command_name.startswith("autorole"):
            return
        collection = self.bot.get_guild_main_collection(ctx.guild_id)

        if ctx.focused_option == "name":
            autoroles = collection.find_one({"_id": "autorole"})
            del autoroles["_id"]

            choices = [
                create_choice(name=autorole_name, value=autorole_name)
                for autorole_name in autoroles
                if autorole_name.startswith(ctx.user_input)
            ][:25]
        elif ctx.focused_option == "option":
            autoroles = collection.find_one({"_id": "autorole"})
            autorole_data = autoroles.get(ctx.options.get("name"))
            select_options = [
                option["label"] for option in autorole_data["component"]["options"]
            ]
            choices = [
                create_choice(name=option_name, value=option_name)
                for option_name in select_options
                if option_name.startswith(ctx.user_input)
            ][:25]
        elif ctx.focused_option == "role":
            configuration_data = collection.find_one({"_id": "configuration"})
            on_join_roles = [
                ctx.guild.get_role(role_id)
                for role_id in configuration_data.get("on_join_roles")
            ]
            choices = [
                create_choice(name=role.name, value=str(role.id))
                for role in on_join_roles
                if role.name.startswith(ctx.user_input)
            ][:25]
        await ctx.populate(choices)

    @slash_subcommand(
        base="autorole",
        subcommand_group="on_join",
        name="add",
        description="Adds a new on join role",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_on_join_add(self, ctx: SlashContext, role: Role):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_ON_JOIN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "configuration"}, {"$push": {"on_join_roles": role.id}}
        )

        await ctx.send(content["ROLE_ADDED_TEXT"].format(role=role.mention))

    @slash_subcommand(
        base="autorole",
        subcommand_group="on_join",
        name="remove",
        description="Removes on join role",
        options=[
            create_option(
                name="role",
                description="Role which gives when member has joined to server",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            )
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_on_join_remove(self, ctx: SlashContext, role: str):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_ON_JOIN", lang)

        role = ctx.guild.get_role(int(role))

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "configuration"}, {"$pull": {"on_join_roles": role.id}}, upsert=True
        )

        await ctx.send(content["ROLE_REMOVED_TEXT"].format(role=role.mention))

    # SELECT ROLE

    @Cog.listener()
    async def on_select_option(self, ctx: ComponentContext):
        if ctx.custom_id != "autorole_select":
            return

        values = ctx.selected_options
        added_roles = []
        removed_roles = []

        for _role in values:
            role: Role = ctx.guild.get_role(int(_role))
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
                removed_roles.append(f"`{role.name}`")
            else:
                await ctx.author.add_roles(role)
                added_roles.append(f"`{role.name}`")

        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)
        message_content = ""
        if added_roles:
            message_content += content["ADDED_ROLES_TEXT"] + ", ".join(added_roles)
        if removed_roles:
            message_content += content["REMOVED_ROLES_TEXT"] + ", ".join(removed_roles)

        await ctx.send(content=message_content, hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="create",
        description="Creating new dropdown",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_create_dropdown(
        self,
        ctx: SlashContext,
        name: str,
        message_content: str,
        placeholder: str = None,
    ):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)
        components = [
            Select(
                placeholder=placeholder
                if placeholder is not None
                else content["NO_OPTIONS_TEXT"],
                options=[SelectOption(label="None", value="None")],
                disabled=True,
                id="autorole_select",
            )
        ]

        message = await ctx.channel.send(content=message_content, components=components)
        await ctx.send(content["CREATED_DROPDOWN_TEXT"], hidden=True)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "autorole"},
            {
                "$set": {
                    name: {
                        "content": message_content,
                        "message_id": message.id,
                        "autorole_type": "select_menu",
                        "component": components[0].to_dict(),
                    }
                }
            },
            upsert=True,
        )

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="add_option",
        description="Adding role to dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="option_name",
                description="The name of option",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="role", description="Role for option", option_type=8, required=True
            ),
            create_option(
                name="emoji",
                description="The emoji for option",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
            create_option(
                name="description",
                description="The description of option",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_add_option(
        self,
        ctx: SlashContext,
        name: str,
        option_name: str,
        role: Role,
        emoji: str = None,
        description: str = None,
    ):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autoroles = collection.find_one({"_id": "autorole"})
        if autoroles is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])
        autorole_data = autoroles.get(name)
        if autorole_data is None:
            return await ctx.send(content["DROPDOWN_NOT_FOUND"])
        message_id = autorole_data["message_id"]

        original_message: ComponentMessage = await ctx.channel.fetch_message(
            int(message_id)
        )
        if not original_message.components:
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"], hidden=True)

        select_component: Select = original_message.components[0].components[0]
        if select_component.custom_id != "autorole_select":
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"], hidden=True)

        if len(select_component.options) == 25:
            return await ctx.send(content["OPTIONS_OVERKILL_TEXT"], hidden=True)

        if emoji:
            emoji = self.get_emoji(emoji)

        if select_component.options[0].label == "None":
            select_component.options = [
                SelectOption(
                    label=option_name,
                    value=f"{role.id}",
                    emoji=emoji,
                    description=description,
                )
            ]
        else:
            select_component.options.append(
                SelectOption(
                    label=option_name,
                    value=f"{role.id}",
                    emoji=emoji,
                    description=description,
                )
            )
        select_component.disabled = False
        if select_component.placeholder == content["NO_OPTIONS_TEXT"]:
            select_component.placeholder = content["SELECT_ROLE_TEXT"]

        select_component.max_values = len(select_component.options)
        await original_message.edit(components=[select_component])
        await ctx.send(content["ROLE_ADDED_TEXT"], hidden=True)

        self._update_db_select(collection, name, select_component)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="remove_option",
        description="Removing role from dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="option",
                description="Option of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_remove_role(
        self, ctx: SlashContext, name: str, option: str
    ):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autoroles = collection.find_one({"_id": "autorole"})
        if autoroles is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])
        autorole_data = autoroles.get(name)
        if autorole_data is None:
            return await ctx.send(content["DROPDOWN_NOT_FOUND"])
        message_id = autorole_data["message_id"]

        original_message: ComponentMessage = await ctx.channel.fetch_message(
            int(message_id)
        )
        if not original_message.components:
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"])

        select_component: Select = original_message.components[0].components[0]
        if select_component.custom_id != "autorole_select":
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"], hidden=True)

        select_options = select_component.options
        for _option in select_options:
            if _option.label == option:
                option_index = select_options.index(_option)
                del select_options[option_index]
                break
        else:
            return await ctx.send(content["OPTION_NOT_FOUND_TEXT"], hidden=True)

        if not select_options:
            return await ctx.send(content["OPTIONS_LESS_THAN_1_TEXT"], hidden=True)

        select_component.max_values = len(select_options)
        await original_message.edit(components=[select_component])
        await ctx.send(content["ROLE_REMOVED_TEXT"], hidden=True)

        self._update_db_select(collection, name, select_component)

    def _update_db_select(
        self, collection: Collection, name: str, select_component: Select
    ):
        collection.update_one(
            {"_id": "autorole"},
            {"$set": {f"{name}.component": select_component.to_dict()}},
            upsert=True,
        )

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="set_status",
        description="Set up status on dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            ),
            create_option(
                name="status",
                description="status of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name="enable", value="enable"),
                    create_choice(name="disable", value="disable"),
                ],
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_set_status(
        self, ctx: SlashContext, name: str, status: str
    ):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autoroles = collection.find_one({"_id": "autorole"})
        if autoroles is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])
        autorole_data = autoroles.get(name)
        if autorole_data is None:
            return await ctx.send(content["DROPDOWN_NOT_FOUND"])
        message_id = autorole_data["message_id"]

        original_message: ComponentMessage = await ctx.channel.fetch_message(
            int(message_id)
        )
        if not original_message.components:
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"], hidden=True)

        select_component: Select = original_message.components[0].components[0]
        if select_component.custom_id != "autorole_select":
            return await ctx.send(content["MESSAGE_WITHOUT_DROPDOWN_TEXT"], hidden=True)

        select_component.disabled = status == "disable"
        message_content = (
            content["DROPDOWN_ENABLED_TEXT"]
            if status == select_component.disabled
            else content["DROPDOWN_DISABLED_TEXT"]
        )

        await original_message.edit(components=[select_component])
        await ctx.send(message_content, hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="load",
        description="Load dropdown from database",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            )
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_load(self, ctx: SlashContext, name: str):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autorole_data = collection.find_one({"_id": "autorole"})
        if autorole_data is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])
        message_data = autorole_data.get(name)
        if message_data is None:
            return await ctx.send(content["DROPDOWN_NOT_FOUND"])

        select_component = Select.from_json(message_data["component"])

        await ctx.channel.send(
            content=message_data["content"], components=[select_component]
        )
        await ctx.send(content["DROPDOWN_LOADED_TEXT"], hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="list",
        description="Show list of saved dropdowns",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_list(self, ctx: SlashContext):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autorole_data = collection.find_one({"_id": "autorole"})
        if autorole_data is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])

        embed = Embed(
            title=content["DROPDOWN_LIST"],
            description="",
            color=self.bot.get_embed_color(ctx.guild_id),
        )

        del autorole_data["_id"]
        for count, dropdown in enumerate(autorole_data, start=1):
            embed.description += f"**{count}. {dropdown}**\n"

        await ctx.send(embed=embed, hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="delete",
        description="Deletes dropdown from database. Doesn't delete message!",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            )
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_delete(self, ctx: SlashContext, name: str):
        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autorole_data = collection.find_one({"_id": "autorole"})
        if autorole_data is None:
            return await ctx.send(content["NOT_SAVED_DROPDOWNS"])
        message_data = autorole_data.get(name)
        if message_data is None:
            return await ctx.send(content["DROPDOWN_NOT_FOUND"])
        
        collection.update_one(
            {"_id": "autorole"},
            {
                "$unset": {
                    name: ""
                }
            }
        )

        await ctx.send(content["DROPDOWN_DELETED_TEXT"])

    # REACTION ROLE COMMANDS AND EVENTS

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.member.bot:
            return
        try:
            _cog_is_enabled(self, payload.guild_id)
        except CogDisabledOnGuild:
            return

        collection = self.bot.get_guild_main_collection(payload.guild_id)
        message_ids = collection.find_one({"_id": "reaction_roles"})
        if message_ids is None:
            return

        post = message_ids.get(str(payload.message_id))
        if post is None:
            return
        emoji = payload.emoji.id
        if payload.emoji.id is None:
            emoji = payload.emoji

        guild: Guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            guild = await self.bot.fetch_guild(payload.guild_id)

        emoji_role = self.get_emoji_role(collection, payload.message_id, emoji)
        if emoji_role is None:
            return
        role = guild.get_role(emoji_role)

        await payload.member.add_roles(role)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        try:
            _cog_is_enabled(self, payload.guild_id)
        except CogDisabledOnGuild:
            return

        collection = self.bot.get_guild_main_collection(payload.guild_id)
        message_ids = collection.find_one({"_id": "reaction_roles"})
        if message_ids is None:
            return

        post = message_ids.get(str(payload.message_id))
        if post is None:
            return

        emoji = payload.emoji.id
        if payload.emoji.id is None:
            emoji = payload.emoji

        guild: Guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            guild = await self.bot.fetch_guild(payload.guild_id)

        emoji_role = self.get_emoji_role(collection, payload.message_id, emoji)
        if emoji_role is None:
            return
        role = guild.get_role(emoji_role)

        member = guild.get_member(payload.user_id)
        if member is None:
            member = guild.fetch_member(payload.user_id)
        await member.remove_roles(role)

    def get_emoji_role(self, collection, message_id: int, emoji):
        message_ids = collection.find_one({"_id": "reaction_roles"})
        message_roles = message_ids.get(str(message_id))
        return message_roles.get(str(emoji))

    @slash_subcommand(
        base="reactionrole",
        subcommand_group="add",
        name="post",
        description="Adds new message to react",
        options=[
            create_option(
                name="message_id",
                description="Message id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            )
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def add_post(self, ctx: SlashContext, message_id: str):
        collection = self.bot.get_guild_main_collection(ctx.guild.id)
        collection.update_one(
            {"_id": "reaction_roles"}, {"$set": {message_id: {}}}, upsert=True
        )

        await ctx.send("✅", hidden=True)

    @slash_subcommand(
        base="reactionrole",
        subcommand_group="add",
        name="role",
        description="Add reaction role to message",
        options=[
            create_option(
                name="message_id",
                description="Message id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="emoji",
                description="emoji or emoji id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="role", description="role for emoji", option_type=8, required=True
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def add_emoji_role(self, ctx: SlashContext, message_id, emoji, role: Role):
        if emoji[0] == "<":
            emoji = emoji.split(":")[2].replace(">", "")

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "reaction_roles"},
            {"$set": {f"{message_id}.{emoji}": role.id}},
            upsert=True,
        )

        await ctx.send("✅", hidden=True)

    @slash_subcommand(
        base="reactionrole",
        subcommand_group="remove",
        name="post",
        description="Remove's reaction roles message from database. Doesn't delete message.",
        options=[
            create_option(
                name="message_id",
                description="Message id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
        ],
    )
    @bot_owner_or_permissions(manage_roles=True)
    @is_enabled()
    async def remove_post(self, ctx: SlashContext, message_id: str):
        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one({"_id": "reaction_roles"}, {"$set": {message_id: ""}})

        await ctx.send("✅", hidden=True)

    @slash_subcommand(
        base="reactionrole",
        subcommand_group="remove",
        name="role",
        description="Remove reaction role from message",
        options=[
            create_option(
                name="message_id",
                description="Message id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="emoji",
                description="emoji or emoji id",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
        ],
    )
    @bot_owner_or_permissions(manage_roles=True)
    @is_enabled()
    async def remove_role(self, ctx: SlashContext, message_id: str, emoji: str):
        if emoji[0] == "<":
            emoji = emoji.split(":")[2].replace(">", "")

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "reaction_roles"}, {"$unset": {f"{message_id}.{emoji}": ""}}
        )

        await ctx.send("✅", hidden=True)

    @slash_subcommand(
        base="autorole",
        name="add_role_to_everyone",
        description="Adds role to everyone member on server",
    )
    async def autorole_add_role_to_everyone(self, ctx: SlashContext, role: Role):
        await ctx.defer()
        for member in ctx.guild.members:
            if role not in member.roles:
                await member.add_roles(role)
        await ctx.send("☑️", hidden=True)

    @slash_subcommand(
        base="autorole",
        name="remove_role_from_everyone",
        description="Removes role from everyone member on server",
    )
    async def autorole_remove_role_from_everyone(self, ctx: SlashContext, role: Role):
        await ctx.defer()
        for member in ctx.guild.members:
            if role in member.roles:
                await member.remove_roles(role)
        await ctx.send("☑️", hidden=True)

    # Button AutoRole
    @Cog.listener()
    async def on_button_click(self, ctx: ComponentContext):
        if not ctx.custom_id.startswith("autorole_button"):
            return
        content = get_content(
            "AUTOROLE_BUTTON", lang=self.bot.get_guild_bot_lang(ctx.guild_id)
        )
        role_id = ctx.custom_id.split("|")[1]
        role = ctx.guild.get_role(int(role_id))
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.send(
                content["EVENT_REMOVED_ROLE_TEXT"].format(role.mention), hidden=True
            )
        else:
            await ctx.author.add_roles(role)
            await ctx.send(
                content["EVENT_ADDED_ROLE_TEXT"].format(role.mention), hidden=True
            )

    @slash_subcommand(
        base="autorole",
        subcommand_group="button",
        name="create",
        description="Send a message for adding buttons",
    )
    async def autorole_button_create(
        self, ctx: SlashContext, name: str, message_content: str
    ):
        await ctx.defer(hidden=True)

        message = await ctx.channel.send(message_content)
        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        collection.update_one(
            {"_id": "autorole"},
            {
                "$set": {
                    name: {
                        "content": message_content,
                        "autorole_type": "buttons",
                        "message_id": message.id,
                    }
                }
            },
            upsert=True,
        )
        content = get_content(
            "AUTOROLE_BUTTON", self.bot.get_guild_bot_lang(ctx.guild_id)
        )
        await ctx.send(content["AUTOROLE_CREATED"], hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="button",
        name="add_role",
        description="Adds a new button with role",
        options=[
            create_option(
                name="name",
                description="The name of group of buttons",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="role", description="Role", option_type=8, required=True
            ),
            create_option(
                name="label",
                description="The label of button",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
            create_option(
                name="style",
                description="The style or color of button",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
                choices=[
                    create_choice(name="Blue", value=ButtonStyle.blue.value),
                    create_choice(name="Gray", value=ButtonStyle.gray.value),
                    create_choice(name="Green", value=ButtonStyle.green.value),
                    create_choice(name="Red", value=ButtonStyle.red.value),
                ],
            ),
            create_option(
                name="emoji",
                description="The emoji of button",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
        ],
    )
    async def autorole_button_add_role(
        self,
        ctx: SlashContext,
        name: str,
        role: Role,
        label: str = None,
        style: int = None,
        emoji: str = None,
    ):
        await ctx.defer(hidden=True)
        content = get_content(
            "AUTOROLE_BUTTON", self.bot.get_guild_bot_lang(ctx.guild_id)
        )
        if not label and not emoji:
            return await ctx.send(content["AT_LEAST_LABEL_EMOJI_TEXT"])

        collection = self.bot.get_guild_main_collection(ctx.guild_id)
        autoroles = collection.find_one({"_id": "autorole"})
        autorole = autoroles.get(name)
        if autorole["autorole_type"] != "buttons":
            return await ctx.send(content["NOT_BUTTONS_AUTOROLE"])

        button = Button(
            label=label,
            emoji=self.get_emoji(emoji) if emoji else None,
            style=style or ButtonStyle.gray,
            custom_id=f"autorole_button|{role.id}",
        )
        original_message = await ctx.channel.fetch_message(int(autorole["message_id"]))
        original_components = original_message.components
        if not original_components:
            original_components = [button]
        else:
            for row in original_components:
                if len(row) < 5 and not isinstance(row[0], Select):
                    row.append(button)
                    break
            else:
                if len(original_components) == 5:
                    return await ctx.send(content["LIMIT_25_BUTTONS"])
                else:
                    original_components.append([button])

        await original_message.edit(components=original_components)
        await ctx.send(content["COMMAND_ROLE_ADDED_TEXT"], hidden=True)

        collection.update_one(
            {"_id": "autorole"},
            {
                "$set": {
                    f"{name}.component": [
                        actionrow.to_dict() for actionrow in original_components
                    ]
                }
            },
            upsert=True,
        )

    def get_emoji(self, emoji: str):
        if emoji.startswith("<"):
            _emoji = emoji.split(":")[-1].replace(">", "")
            emoji = self.bot.get_emoji(int(_emoji))
        return emoji


def setup(bot):
    bot.add_cog(AutoRole(bot))
