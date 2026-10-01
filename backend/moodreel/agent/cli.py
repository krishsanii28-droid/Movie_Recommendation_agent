"""Chat with the agent in your terminal: ``python -m moodreel.agent.cli``."""

from __future__ import annotations

import argparse
import asyncio
import textwrap

from moodreel.log import setup_logging
from moodreel.schemas import ChatRequest, GroupMember, GroupRequest


async def main_async(args: argparse.Namespace) -> None:
    from moodreel.services import get_agent

    agent = get_agent()
    agent.typing_delay = 0
    print("🎬 MoodReel — how are you feeling right now? (Ctrl+C to quit)\n")
    session_id = None
    if args.group:
        members = [
            GroupMember(name=p.split(":", 1)[0], mood=p.split(":", 1)[1]) for p in args.group
        ]
        reply = await agent.collect(
            agent.stream_group(GroupRequest(user_id=args.user, members=members))
        )
        render(reply)
        return
    while True:
        try:
            text = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        req = ChatRequest(
            user_id=args.user, session_id=session_id, message=text, languages=args.lang or []
        )
        reply = await agent.collect(agent.stream(req))
        session_id = reply.session_id
        render(reply)


def render(reply) -> None:
    if reply.mood:
        print(f"   [mood: {reply.mood.summary} | tones: {', '.join(reply.mood.target_tones[:5])}]")
    if reply.care:
        print("\n💛 " + textwrap.fill(reply.care.text, 90))
        for h in reply.care.helplines:
            print(f"   • {h['name']}: {h['contact']}")
    print(f"\nmoodreel › {reply.message}")
    if reply.options:
        print("   options: " + " / ".join(reply.options))
    for r in reply.recommendations:
        m = r.movie
        stream = ", ".join(p.name for p in m.providers.stream) or "check JustWatch"
        print(
            f"\n  • [{r.slot}] {m.title} ({m.year}, {m.language_name}) ★{m.rating} · {m.runtime} min · {stream}"
        )
        print(textwrap.indent(textwrap.fill(r.reason, 88), "      "))
    print(f"\n   ({reply.engine} · {len(reply.steps)} tool steps)\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="moodreel.agent.cli")
    parser.add_argument("--user", default="cli-user")
    parser.add_argument("--lang", nargs="*", help="language filter, e.g. ml ta")
    parser.add_argument(
        "--group", nargs="*", help='group mode, e.g. "Asha:exhausted" "Ravi:want to laugh"'
    )
    parser.add_argument("--verbose", action="store_true", help="log agent steps")
    args = parser.parse_args()
    setup_logging("INFO" if args.verbose else "WARNING")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
