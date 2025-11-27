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


def build_category_pie_chart(category_totals: list[tuple[str, float]], title: str) -> BytesIO:
    """Create pie chart from category totals with absolute amounts."""
    labels = [item[0] for item in category_totals]
    values = [item[1] for item in category_totals]
    if not values or sum(values) == 0:
        raise ValueError("Category totals must contain positive values")
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Create custom autopct function to show percentage and absolute value
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f"{pct:.1f}%\n({val:.0f} ₽)"
        return my_autopct
    
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct=make_autopct(values),
        textprops={"color": "w", "fontsize": 9},
        pctdistance=0.85,
    )
    ax.set_title(title, fontsize=12, fontweight="bold")
    for text in texts:
        text.set_color("black")
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(8)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer
