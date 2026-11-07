"""egitim.py'yi (# %% hücreli) Kaggle'a yüklenecek egitim.ipynb'e çevirir: python ml/kaggle/defter_yap.py"""
import json
import re
from pathlib import Path

K = Path(__file__).parent
hucre = []
for parca in re.split(r"^# %%", (K / "egitim.py").read_text(encoding="utf-8"), flags=re.M)[1:]:
    md = parca.startswith(" [markdown]")
    satir = parca.split("\n", 1)[1].strip("\n").split("\n")
    if md:
        satir = [re.sub(r"^# ?", "", s) for s in satir]
    hucre.append({"cell_type": "markdown" if md else "code", "metadata": {}, "source": [s + "\n" for s in satir[:-1]] + satir[-1:],
                  **({} if md else {"execution_count": None, "outputs": []})})
nb = {"cells": hucre, "nbformat": 4, "nbformat_minor": 5,
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}, "language_info": {"name": "python"}}}
(K / "egitim.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(hucre), "hücre ->", K / "egitim.ipynb")
