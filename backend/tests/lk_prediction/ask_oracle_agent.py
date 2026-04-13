"""
Ask Oracle Agent — The intelligent command-line interface for the Lal Kitab Agent.

This CLI uses the LalKitabAgent which can plan its own work, fetch charts, 
run predictions, and maintain memory of the user.

Usage:
    python tests/lk_prediction/ask_oracle_agent.py --user sachin
"""
import os
import sys
import argparse

# Add backend to path
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from astroq.lk_prediction.agent.lk_agent import LalKitabAgent

def main():
    parser = argparse.ArgumentParser(description="Lal Kitab Oracle Agent v2")
    parser.add_argument("--user", type=str, default="guest", help="Client name or ID for memory context.")
    parser.add_argument("--no-memory", action="store_true", help="Disable Honcho/Local memory.")
    parser.add_argument("--clear", action="store_true", help="Clear memory before starting.")
    args = parser.parse_args()

    # Clear memory if requested
    if args.clear:
        mem_path = os.path.join(_BACKEND, f"data/memory_{args.user}.json")
        if os.path.exists(mem_path):
            os.remove(mem_path)
            print(f"✨ Memory for user '{args.user}' has been cleared.")

    # Clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')

    print("=========================================================")
    print("    🔮  LAL KITAB ORACLE AGENT (Version 2.0)  🔮      ")
    print("=========================================================")
    print(f"  Mode: Intelligent Tool Dispatcher + Memory")
    print(f"  User ID: {args.user}")
    print(f"  Memory Status: {'OFF' if args.no_memory else 'ON (Honcho/Local)'}")
    print("=========================================================\n")

    # Initialize the agent
    agent = LalKitabAgent(user_id=args.user, use_memory=not args.no_memory)

    print("The system is ready. Ask anything about your chart, marriage, ")
    print("career, or specific time periods (e.g. 'How is my age 29?').")
    print("(Type 'exit' or press Ctrl+C to disconnect)\n")

    try:
        while True:
            question = input("❓ Question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ("exit", "quit", "q"):
                print("\nFarewell! The heavens keep your secrets until we meet again. ✨")
                break
                
            # The agent handles planning, tool execution, and final streaming output
            agent.ask(question)
            
            print("\n" + "-"*55)
            
    except KeyboardInterrupt:
        print("\n\nFarewell! The heavens keep your secrets until we meet again. ✨")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
