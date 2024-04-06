import json
import datetime
import math
import requests
import time
import logging
import os
import urllib.parse
from pprint import pprint

# TODO: Add folder to save files to
# TODO: When searching from the middle, script does not know when to complete.


class DiscordSearcher:
    """
    A class for searching messages in a Discord guild using the Discord API.
    """

    def __init__(self, token: str):
        if not token:
            raise ValueError("Token is required")
        self.token = token
        self.filename = None
        self.query = None
        self.error_count = 0
        self.MAX_ERROR = 5
        self.DISCORD_API_OFFSET_LIMIT = 401
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def set_file(self, filename: str) -> None:
        """Set the file to write to."""
        self.filename = filename

    def append_message(self, messages: dict) -> None:
        """Append a message to the file."""
        if self.filename is None:
            raise ValueError("No file set to write to")
        with open(self.filename, "a") as f:
            for message in messages["messages"]:
                f.write(json.dumps(message) + "\n")

    def convert_to_discord_snowflake(self, date: datetime.datetime) -> str:
        """Convert a datetime object to a Discord timestamp."""
        DISCORD_EPOCH = 1420070400000

        timestamp_ms = int(date.timestamp() * 1000)
        timestamp_ms = (timestamp_ms - DISCORD_EPOCH) << 22
        return str(timestamp_ms)

    def form_search_query(
        self,
        guild_id: str,
        content: str | None = None,
        channel_id: str | None = None,
        after: int | datetime.datetime | None = None,
        before: int | datetime.datetime | None = None,
    ) -> None:
        """Form a search query for Discord's Search API."""
        if not guild_id:
            raise ValueError("Guild ID is required")

        base_url = f"https://discord.com/api/v9/guilds/{guild_id}/messages/search?"
        query_params = []

        if content is not None:
            query_params.append(f"content={urllib.parse.quote(content)}")
        if channel_id is not None:
            query_params.append(f"channel_id={channel_id}")

        query_params.extend(
            ["include_nsfw=true", "sort_by=timestamp", "sort_order=asc"]
        )

        if isinstance(after, datetime.datetime):
            query_params.append(f"min_id={self.convert_to_discord_snowflake(after)}")
        elif isinstance(after, int):
            query_params.append(f"min_id={after}")

        if isinstance(before, datetime.datetime):
            query_params.append(f"max_id={self.convert_to_discord_snowflake(before)}")
        elif isinstance(before, int):
            query_params.append(f"max_id={before}")

        search_query = base_url + "&".join(query_params)
        self.query = search_query

    def search(self, query: str) -> dict:
        """Given a search query, return the search results."""
        while True:
            response: requests.Response = requests.get(
                query,
                headers={
                    "authorization": self.token,
                    # "Sec-Ch-Ua": '"Brave";v="123", "Not?A_Brand";v="8", "Chromium";v="123"',
                    # "Sec-Ch-Ua-Mobile": "?0",
                    # "Sec-Ch-Ua-Platform": '"Windows"',
                    # "Sec-Fetch-Dest": "empty",
                    # "Sec-Fetch-Mode": "cors",
                    # "Sec-Fetch-Site": "same-origin",
                    # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    # "X-Debug-Options": "bugReporterEnabled",
                    # "X-Discord-Locale": "en-GB",
                    # "X-Discord-Timezone": "Asia/Singapore",
                    # "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLUdCIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMy4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIzLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjI4MTgwOSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=",
                },
            )
            if response.status_code == 429:
                error = response.json()
                retry_after = error["retry_after"]
                logging.warning(f"Rate limited, retrying in {retry_after} seconds")
                time.sleep(retry_after)
                continue
            elif response.status_code == 200:
                return response.json()
            else:
                self.error_count += 1
                logging.error(f"Error: {response.status_code}, {response.text}")
                if self.error_count == self.MAX_ERROR:
                    raise Exception("Max errors reached")
                time.sleep(5)

    def test_search(self) -> None:
        """Test the search function."""
        self.query = "https://discord.com/api/v9/guilds/791280644939841536/messages/search?content=shadow%20raid&include_nsfw=true&sort_by=timestamp&sort_order=asc"
        self.append_message(self.search(self.query))

    def _update_query_params(self, last_message_timestamp: str) -> None:
        """Update the query parameters with the last message ID."""
        if self.query is None:
            raise ValueError("No query set")
        if "min_id" in self.query:
            min_id = self.query[self.query.index("min_id=") + len("min_id=") :]
            self.query = self.query.replace(min_id, last_message_timestamp)
        else:
            self.query = f"{self.query}&min_id={last_message_timestamp}"

    def test_offset_limit(self) -> None:
        """Test the offset limit of the Discord API."""
        self.query = "https://discord.com/api/v9/guilds/558322816416743459/messages/search?content=BaelzNeuronActivation&include_nsfw=true&sort_by=timestamp&sort_order=asc"
        result = self.search(f"{self.query}&offset=5000")
        pprint(result)
        last_message_id = result["messages"][-1][0]["id"]
        self._update_query_params(last_message_id)
        request_count = 1
        result = self.search(f"{self.query}&offset={(request_count - 1) * 25}")
        pprint(result)

    def retrieve_query_results(self) -> None:
        """Get all results from the search query."""
        if self.query is None:
            raise ValueError("No query set")

        result = self.search(self.query)
        total_results = result["total_results"]
        total_request_needed = math.ceil(total_results / 25)
        request_count = 1
        total_request_count = 1

        logging.info(
            f"Total results: {total_results}, iterating {total_request_needed} times"
        )

        try:
            while True:
                self.append_message(result)
                logging.info(f"Request {total_request_count}/{total_request_needed}")

                if len(result["messages"]) == 0:
                    # We are done
                    break

                if request_count >= self.DISCORD_API_OFFSET_LIMIT:
                    last_message_snowflake: str = result["messages"][-1][0]["id"]
                    self._update_query_params(last_message_snowflake)
                    request_count = 0

                request_count += 1
                total_request_count += 1
                result = self.search(f"{self.query}&offset={(request_count - 1) * 25}")

        except KeyboardInterrupt:
            logging.warning("Search interrupted by user")
        except Exception as e:
            logging.error(f"Error occurred during search: {str(e)}")
        finally:
            print(f"Total requests made: {total_request_count}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    searcher = DiscordSearcher(token)
    searcher.set_file("TowaShrug.json")
    searcher.form_search_query("558322816416743459", "TowaShrug")
    searcher.retrieve_query_results()
    # searcher.set_file("TowaShrug.json")
    # searcher.form_search_query(
    #     "558322816416743459", "TowaShrug", after=datetime.datetime(2022, 6, 1)
    # )
