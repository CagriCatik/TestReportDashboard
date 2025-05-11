# model/report.py
import pandas as pd
from enum import Enum
from io import BytesIO
import matplotlib.pyplot as plt


class TestStatus(Enum):
    PASS = "Pass"
    FAIL = "Fail"
    NOT_TESTED = "Not Tested"


class TestReport:
    """
    Model for test report data: holds DataFrame and provides stats & I/O methods.
    """
    def __init__(self, records=None):
        # Initialize DataFrame with correct columns
        self.df = pd.DataFrame(records or [], columns=[
            'Test Case ID', 'Test Case Description', 'Test Status', 'Comments'
        ])

    def load_from_excel(self, path: str) -> None:
        # Load Excel into DataFrame
        df = pd.read_excel(path)
        # Normalize column names: strip whitespace
        col_map = {col: col.strip() for col in df.columns}
        df.rename(columns=col_map, inplace=True)
        # Required columns (case-insensitive)
        required = ['test case id', 'test case description', 'test status', 'comments']
        mapping = {}
        for r in required:
            for orig in df.columns:
                if orig.lower() == r:
                    mapping[orig] = {
                        'test case id': 'Test Case ID',
                        'test case description': 'Test Case Description',
                        'test status': 'Test Status',
                        'comments': 'Comments'
                    }[r]
                    break
        # Validate presence
        if len(mapping) < len(required):
            missing = set(['Test Case ID', 
                           'Test Case Description', 
                           'Test Status', 
                           'Comments']) - set(mapping.values())
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        # Select and rename
        self.df = df[list(mapping.keys())].rename(columns=mapping)

    def summary(self) -> dict:
        """
        Returns dict with total count, counts per status, and percentages.
        """
        total = len(self.df)
        counts = {
            TestStatus.PASS.value: int((self.df['Test Status'] == TestStatus.PASS.value).sum()),
            TestStatus.FAIL.value: int((self.df['Test Status'] == TestStatus.FAIL.value).sum()),
            TestStatus.NOT_TESTED.value: int((self.df['Test Status'] == TestStatus.NOT_TESTED.value).sum()),
        }
        percentages = {
            status: f"{(count/total*100):.1f}%" if total else "0.0%"
            for status, count in counts.items()
        }
        return {'total': total, 'counts': counts, 'percent': percentages}

    def pie_chart_bytes(self) -> bytes:
        """
        Builds a high-quality pie chart of test-status breakdown and returns PNG bytes.
        """
        stats  = self.summary()
        labels = [
            TestStatus.PASS.value,
            TestStatus.FAIL.value,
            TestStatus.NOT_TESTED.value
        ]
        sizes  = [stats['counts'][lbl] for lbl in labels]
        explode = (0.1, 0, 0)

        # Define your colors in the same order as labels
        colors = ['green', 'red', 'grey']

        # 1) Larger figure + higher base DPI
        fig, ax = plt.subplots(figsize=(6, 6), dpi=150)

        # 2) Crisp white borders between wedges
        wedge_props = {'linewidth': 1, 'edgecolor': 'white'}

        # 3) Draw the pie with custom colors
        patches, texts, autotexts = ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,               # ← custom colors here
            autopct='%1.1f%%',
            pctdistance=0.8,
            labeldistance=1.05,
            shadow=False,
            startangle=140,
            wedgeprops=wedge_props,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        ax.axis('equal')  # Keep it a circle

        # 4) Title
        ax.set_title("Test Status Breakdown", fontsize=14, weight='bold', pad=20)

        # 5) Save to buffer at high DPI
        buf = BytesIO()
        fig.savefig(
            buf,
            format='png',
            dpi=300,                # final output DPI
            bbox_inches='tight',
            transparent=False
        )
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()