from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "samples" / "documents" / "device-maintenance-handbook.pdf"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(OUTPUT), pagesize=A4, invariant=1)
    canvas.setTitle("Device Maintenance Handbook")
    canvas.setAuthor("Enterprise Knowledge Search")

    _page(
        canvas,
        title="Device Maintenance Handbook",
        heading="Maintenance Window",
        lines=[
            "Gateway firmware maintenance is scheduled for Wednesday at 22:00 UTC.",
            "Operators confirm that the device has reported a healthy heartbeat within",
            "the previous fifteen minutes before starting an update.",
            "",
            "Updates proceed in batches of ten devices. The operator pauses the rollout",
            "when more than one device in a batch fails its post-update health check.",
        ],
    )
    canvas.showPage()
    _page(
        canvas,
        title="Device Maintenance Handbook",
        heading="Rollback and Verification",
        lines=[
            "The previous signed firmware image remains available for rollback.",
            "A rollback is required when a gateway cannot reconnect within five minutes",
            "or when telemetry validation reports an incompatible schema.",
            "",
            "After maintenance, operators verify connectivity, clock synchronization,",
            "telemetry delivery, and the installed firmware version. The change record",
            "contains the affected device identifiers and the final outcome.",
        ],
    )
    canvas.save()


def _page(canvas: Canvas, *, title: str, heading: str, lines: list[str]) -> None:
    _, page_height = A4
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(64, page_height - 72, title)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(64, page_height - 112, heading)
    canvas.setFont("Helvetica", 11)
    y = page_height - 142
    for line in lines:
        canvas.drawString(64, y, line)
        y -= 18


if __name__ == "__main__":
    main()
