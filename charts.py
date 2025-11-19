import matplotlib

matplotlib.use("Agg")

from io import BytesIO

from matplotlib import pyplot as plt


def build_period_snapshot_chart(today_total: float, month_total: float) -> BytesIO:
    """Build a bar image that compares daily and monthly totals."""
    values = [today_total, month_total]
    labels = ["Сегодня", "За месяц"]
    colors = ["#4CAF50", "#2196F3"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=colors)
    ax.set_title("Сравнение трат")
    ax.set_ylabel("Сумма, ₽")
    max_value = max(values) or 1.0
    for index, value in enumerate(values):
        ax.text(index, value + max_value * 0.02, f"{value:.2f}", ha="center")
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer
