#!/usr/bin/env python3
"""
Lightweight cost / usage pointers for OpenAI.

OpenAI does not expose a simple public "remaining balance" API for all accounts.
This script prints authoritative links and explains where token usage is logged locally.

During each run, the agent logs per-call usage and end-of-pipeline token totals to ai_news_agent.log
(search for "OpenAI usage" and "prompt_tokens").
"""

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    print("OpenAI usage dashboard (browser): https://platform.openai.com/usage")
    print("API pricing reference: https://openai.com/pricing")
    print(
        "Local logs: grep -n \"OpenAI usage\\|prompt_tokens\\|completion_tokens\" ai_news_agent.log"
    )


if __name__ == "__main__":
    main()
