"""Synthetic viewer fixture. This is deliberately NOT an ECHO agent or ARC score."""
import json
import time


def main():
    for step in range(24):
        grid = [[0] * 32 for _ in range(24)]
        for y in range(24):
            for x in range(32):
                if x in (0, 31) or y in (0, 23) or (x in (11, 20) and y not in (7, 8, 17, 18)):
                    grid[y][x] = 11
        grid[18][28] = 4
        for x in range(2, min(29, step + 3)):
            grid[7][x] = 1
        grid[7][min(29, step + 3)] = 10
        print(json.dumps({"kind": "frame", "origin": "DEMO · fixture sintética, no ECHO",
                          "grid": grid, "turn": step, "text": f"Frame sintético {step + 1}/24"}), flush=True)
        time.sleep(0.14)
    print(json.dumps({"kind": "result", "origin": "DEMO", "text": "Visor completado. No mide inteligencia ni ARC."}), flush=True)


if __name__ == "__main__":
    main()
