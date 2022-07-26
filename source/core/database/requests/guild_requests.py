from ..consts import AsyncMongoClient, DocumentType, OperatorType


class GuildRequests:
    def __init__(self, client: AsyncMongoClient):
        self._client = client
        self._database = client["guilds"]

    def __get_collection(self, *keys):
        collection = self._database
        for key in keys:
            collection = collection[str(key)]
        return collection

    async def get_guild_raw_data(self, guild_id: int):
        main_collection = self.__get_collection(guild_id, "configuration")
        users_collection = self.__get_collection(guild_id, "users")
        data = [doc async for doc in main_collection.find()]
        users_data = [doc async for doc in users_collection.find()]

        full_data = {}
        for document in data:
            id = document["_id"]
            match id:
                case "tags" | "autoroles":
                    full_data[id] = document[id]
                case "voice_time":
                    del document["_id"]
                    full_data[id] = document
                case _:
                    full_data[id] = document
        full_data["users"] = users_data
        return full_data

    async def __insert_document(self, *keys, data: dict):
        collection = self.__get_collection(*keys)
        await collection.insert_one(data)

    async def __update_document(
        self,
        *keys,
        filter: DocumentType | str | dict,
        operator: OperatorType,
        data: dict,
        upsert: bool = True
    ):
        collection = self.__get_collection(*keys)
        _filter = {"_id": filter} if isinstance(filter, (str, DocumentType)) else filter
        await collection.update_one(_filter, {operator: data}, upsert)

    async def update_document(
        self, guild_id: int, document: DocumentType | str | dict, operator: OperatorType, data: dict
    ):
        await self.__update_document(
            guild_id, "configuration", filter=document, operator=operator, data=data
        )

    async def add_guild(self, guild_id: int) -> dict:
        data = {"_id": "configuration", "language": "en-US"}
        await self.__insert_document(guild_id, "configuration", data=data)
        return data

    async def remove_guild(self, guild_id: int):
        for key in ("configuration", "users"):
            await self._database[str(guild_id)][key].drop()

    async def add_user(self, guild_id: int, user_id: int) -> dict:
        data = {
            "_id": str(user_id),
        }
        await self.__insert_document(guild_id, "users", data=data)
        return data

    async def remove_user(self, guild_id: int, user_id: int):
        data = {
            "_id": str(user_id),
        }
        collection = self.__get_collection(guild_id, "users")
        await collection.delete_one(data)

    async def update_user(self, guild_id: int, user_id: int, data: dict):
        await self.__update_document(
            guild_id, "users", filter=str(user_id), operator=OperatorType.SET, data=data
        )
