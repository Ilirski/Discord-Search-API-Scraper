import json
import datetime
import math
import requests
import time
import logging
import optparse
import os
from typing import Optional
import re


DISCORD_EPOCH = 1420070400000


def to_datetime(snowflake: str, epoch=DISCORD_EPOCH) -> datetime.datetime:
    """Convert a Discord snowflake to a datetime object."""
    milliseconds = int(snowflake) >> 22
    return datetime.datetime.fromtimestamp((milliseconds + epoch) / 1000.0)


def to_snowflake(timestamp: datetime.datetime) -> str:
    """Convert a datetime object to a Discord snowflake."""
    discord_epoch = 1420070400000  # Discord epoch (2015-01-01T00:00:00.000Z)
    milliseconds = int(timestamp.timestamp() * 1000)
    snowflake = (milliseconds - discord_epoch) << 22
    return str(snowflake)


def is_snowflake(snowflake: str) -> bool:
    """Check if a string is a valid Discord snowflake."""
    pattern = r"^\d{17,19}$"
    return bool(re.match(pattern, snowflake))


class DiscordSearcher:
    """
    A class for searching messages in a Discord guild using the Discord API.
    """

    def __init__(
        self,
        guild_id: str,
        token: Optional[str] = None,
        query: Optional[str] = None,
        output: Optional[str] = None,
        channel_id: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> None:
        if not token:
            # Check if token is in environment variable
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                raise ValueError("Token is required")
        if not guild_id:
            raise ValueError("Guild ID is required")
        if after and not is_snowflake(after):
            raise ValueError(f"Invalid snowflake: {after}")
        if before and not is_snowflake(before):
            raise ValueError(f"Invalid snowflake: {before}")
        self.token = token
        self.guild_id = guild_id
        self.query = query
        self.output = output
        self.channel_id = channel_id
        self.after = after
        self.before = before
        self.error_count = 0
        self.MAX_ERROR = 5
        self.DISCORD_API_OFFSET_LIMIT = 400

        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.set_output(output)
        self.form_search_query(guild_id, query, channel_id, after, before)

    def set_output(self, output: Optional[str] = None) -> None:
        """Set the output file."""
        if not output:
            self.output = self.generate_filename()
        else:
            if output.endswith("/"):
                filename = self.generate_filename()
                self.output = os.path.join(output, filename)
            else:
                self.output = output

    def generate_filename(self) -> str:
        """Generate a filename based on the guild ID, query, and timestamp."""
        guild_id = self.guild_id
        query = "_".join(self.query.split()) if self.query else ""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{guild_id}_{query}_{timestamp}.jsonl"
        return filename

    def append_message(self, messages: dict) -> None:
        """Append messages to the output file."""
        with open(self.output, "a") as f:
            for message in messages["messages"]:
                f.write(json.dumps(message) + "\n")

    def form_search_query(
        self,
        guild_id: str,
        content: Optional[str] = None,
        channel_id: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> None:
        """Form a search query for Discord's Search API."""
        if not guild_id:
            raise ValueError("Guild ID is required")

        base_url = f"https://discord.com/api/v9/guilds/{guild_id}/messages/search?"
        query_params = {
            "include_nsfw": "true",
            "sort_by": "timestamp",
            "sort_order": "asc",
        }

        if content is not None:
            query_params["content"] = content
        if channel_id is not None:
            query_params["channel_id"] = channel_id
        if after is not None:
            query_params["min_id"] = after
        if before is not None:
            query_params["max_id"] = before

        search_query = (
            requests.Request("GET", base_url, params=query_params).prepare().url
        )
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

    def _update_query_params(self, last_message_timestamp: str) -> None:
        """Update the query parameters with the last message ID."""
        if self.query is None:
            raise ValueError("No query set")
        if "min_id" in self.query:
            min_id = self.query[self.query.index("min_id=") + len("min_id=") :]
            self.query = self.query.replace(min_id, last_message_timestamp)
        else:
            self.query = f"{self.query}&min_id={last_message_timestamp}"

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
    cliparser = optparse.OptionParser()
    cliparser.add_option("-g", "--guild", dest="guild_id", help="Discord guild ID")
    cliparser.add_option(
        "-t",
        "--token",
        dest="token",
        help="Authentication token. Environment variable: DISCORD_TOKEN.",
    )
    cliparser.add_option(
        "-o",
        "--output",
        dest="output",
        help="Output file or directory path. If a directory is specified, file names will be generated automatically based on the channel names and export parameters. Directory paths must end with a slash to avoid ambiguity.",
    )
    cliparser.add_option("-q", "--query", dest="query", help="Search query")
    cliparser.add_option(
        "-c", "--channel", dest="channel_id", help="Channel ID (optional)"
    )
    cliparser.add_option(
        "-a",
        "--after",
        dest="after",
        help="Only include messages sent after this date or message ID.",
    )
    cliparser.add_option(
        "-b",
        "--before",
        dest="before",
        help="Only include messages sent before this date or message ID.",
    )

    (options, args) = cliparser.parse_args()

    token = options.token
    output = options.output
    guild_id = options.guild_id
    query = options.query
    channel_id = options.channel_id
    after = options.after
    before = options.before

    if not any(vars(options).values()):
        cliparser.print_help()
        cliparser.error("No arguments provided")

    searcher = DiscordSearcher(
        guild_id, token, query, output, channel_id, after, before
    )
    searcher.retrieve_query_results()
