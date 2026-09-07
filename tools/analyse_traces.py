"""Summarise ns2 wireless traces and plot throughput against link rate.

An ns2 trace line begins with an event code: s sent, r received, d dropped,
f forwarded. Fields two and three are the time and the node, and the packet
size sits further along. Throughput is the received bytes over the span of the
run; loss is what was dropped against what was sent.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

EVENTS = {"s", "r", "d", "f"}


@dataclass(frozen=True)
class Summary:
    label: str
    sent: int
    received: int
    dropped: int
    duration: float
    received_bytes: int

    @property
    def throughput_kbps(self) -> float:
        return (self.received_bytes * 8 / self.duration / 1000) if self.duration else 0.0

    @property
    def loss_rate(self) -> float:
        return self.dropped / self.sent if self.sent else 0.0


def summarise(path: Path, label: str) -> Summary:
    sent = received = dropped = received_bytes = 0
    first = last = None

    for line in path.read_text(errors="ignore").splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[0] not in EVENTS:
            continue
        try:
            time = float(fields[1])
        except ValueError:
            continue
        first = time if first is None else min(first, time)
        last = time if last is None else max(last, time)

        # Only the agent layer carries application payload; the MAC layer lines
        # describe the RTS/CTS/ACK exchange around each of those packets.
        if fields[3] != "AGT":
            continue
        size = int(fields[7]) if re.fullmatch(r"\d+", fields[7]) else 0

        if fields[0] == "s":
            sent += 1
        elif fields[0] == "r":
            received += 1
            received_bytes += size
        elif fields[0] == "d":
            dropped += 1

    duration = (last - first) if (first is not None and last is not None) else 0.0
    return Summary(label, sent, received, dropped, duration, received_bytes)


def figure(summaries: list[Summary], output: Path) -> Path:
    labels = [s.label for s in summaries]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.5, 4.2))

    left.bar(labels, [s.throughput_kbps for s in summaries], color="#0969da")
    for i, s in enumerate(summaries):
        left.text(i, s.throughput_kbps, f"{s.throughput_kbps:,.0f}", ha="center",
                  va="bottom", fontsize=10)
    left.set_ylabel("received throughput (kbps)")
    left.set_title("Throughput actually achieved")
    left.grid(axis="y", alpha=0.3)

    right.bar(labels, [100 * s.loss_rate for s in summaries], color="#cf222e")
    for i, s in enumerate(summaries):
        right.text(i, 100 * s.loss_rate, f"{100 * s.loss_rate:.1f}%", ha="center",
                   va="bottom", fontsize=10)
    right.set_ylabel("packets dropped (%)")
    right.set_title("Loss")
    right.grid(axis="y", alpha=0.3)

    fig.suptitle("RTS/CTS wireless simulation across three link rates", fontsize=13)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/throughput.png"))
    args = parser.parse_args()

    traces = [
        (Path("rts-cts-data-ack_1.5Mbps.tr"), "1.5 Mbps"),
        (Path("rts-cts-data-ack_55Mbps.tr"), "55 Mbps"),
        (Path("rts-cts-data-ack_155Mbps.tr"), "155 Mbps"),
    ]
    summaries = [summarise(p, label) for p, label in traces if p.exists()]
    header = f"{'link':<10}{'sent':>8}{'recv':>8}{'drop':>8}{'kbps':>12}{'loss':>8}"
    print(header)
    for s in summaries:
        print(f"{s.label:<10}{s.sent:>8}{s.received:>8}{s.dropped:>8}"
              f"{s.throughput_kbps:>12,.0f}{100 * s.loss_rate:>7.1f}%")
    print(f"\nwrote {figure(summaries, args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def handshake_figure(trace: Path, output: Path, until_ms: float = 20.0) -> Path:
    """Plot which node sent or received each MAC frame over the opening window.

    Grey markers dominate because a frame put on the air is heard by every node
    in range, not only its intended recipient. That is the shared medium the
    RTS/CTS exchange exists to arbitrate.
    """
    colours = {"RTS": "#0969da", "CTS": "#8250df", "message": "#1a7f37", "ACK": "#cf222e"}
    rows = []
    for line in trace.read_text(errors="ignore").splitlines():
        fields = line.split()
        if len(fields) > 6 and fields[0] in "sr" and fields[3] == "MAC":
            time = float(fields[1]) * 1000
            if time <= until_ms:
                rows.append((fields[0], time, fields[2].strip("_"), fields[6]))

    nodes = sorted({node for _, _, node, _ in rows}, key=int)
    position = {node: index for index, node in enumerate(nodes)}

    fig, axis = plt.subplots(figsize=(12.5, 4.4))
    for event, time, node, kind in rows:
        axis.scatter([time], [position[node]], s=90,
                     marker="o" if event == "r" else "s",
                     color=colours.get(kind, "#57606a"),
                     edgecolor="white", linewidth=0.6, zorder=3)

    axis.set_yticks(range(len(nodes)))
    axis.set_yticklabels([f"node {n}" for n in nodes])
    axis.set_xlabel("time (ms)")
    axis.grid(axis="x", alpha=0.3)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k)
               for k, c in colours.items()]
    handles += [plt.Line2D([], [], marker="s", ls="", color="#57606a", label="sent"),
                plt.Line2D([], [], marker="o", ls="", color="#57606a", label="received")]
    axis.legend(handles=handles, ncol=6, fontsize=9, loc="upper center",
                bbox_to_anchor=(0.5, 1.20))
    axis.set_title(f"RTS / CTS / DATA / ACK exchange over the first {until_ms:.0f} ms",
                   fontsize=12, pad=36)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return output
