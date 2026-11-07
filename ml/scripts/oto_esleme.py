"""Bilinmeyen bir Türk levha setinin sınıf adlarını bizim v14 sınıflarına kuralla eşler (Kaggle defteri kullanır).

oto_esleme(adlar) -> (esleme, at, atla):
  esleme: {kaynak_ad: hedef}  hedef bizim sınıf adı ya da ek_veri.py'nin YAYA_RENK'i (yaya geçidi, renkten ayrılır)
  at:     levha olmayan nesneler (trafik ışığı, duba, araç): kutu atılır, görsel kalır
  atla:   tanınmayan ya da belirsiz ad: o sınıfı içeren görsel hiç alınmaz (yanlış etiket riskine girmemek için)
Kurallar ilk eşleşen kazanır; sıra önemli (ör. "ileri ve sağa" "sağa mecburi"den, "demiryolu" "kavşak"tan önce).
Eşleme v9/v14 elle yapılan eşlemelerle tutarlı: ana yol-tali yol kavşağı = crossroads, onarım / refüj = diger_levha.
"""
import re

YAYA = "YAYA_RENK"
AT, ATLA, DIGER = "<at>", "<atla>", "diger_levha"
HIZ = {20: "speed20", 30: "speed30", 40: "speed40", 50: "speed50", 60: "speed60", 70: "speed70"}

KURALLAR = [
    (r"^(kirmizi|sari|yesil|red|green|yellow)(_?(isik|light|lamba))?$|trafik_lamba|^traffic_?light$|^light|duba|cone|bariyer|barrier"
     r"|^(arac|car|vehicle|person|insan|otobus|bus|truck|kamyon|motor|motosiklet|bisikletli|yaya_insan)$", AT),
    (r"onarim|refuj|donus_adasi|her_iki_yandan|ana_yol_sonu|end_of_priority|giremez|truck|kamyon|road_?closed|kapali", DIGER),
    (r"hiz_sonu|sinirlama_sonu|siniri_sonu|end_of_speed|speed_limit_end|end_speed", "hiz_sonu"),
    (r"ada_?etraf", "ada_etrafinda"),
    (r"donel|roundabout", ATLA),  # mavi "ada etrafında" mı üçgen "dönel kavşak" mı belli değil
    (r"duraklama|durak_ve_park|durma_ve_park|no_?stopping|parking_and_stopping", "nostopping"),
    (r"park_?yasak|park_etmek_yasak|no_?parking", "park_yasak"),
    (r"park", "park_yeri"),
    (r"durak|bus_?stop", "durak"),
    (r"demiryol|hemzemin|railway|railroad|level_crossing", "demiryolu"),
    (r"kontrolsuz|kavsa|crossroad|junction|intersection|tali_?yol", "crossroads"),
    (r"isikli|isaret_cihaz|light_?ahead|signal_ahead|trafikisik|trafik_isik", "isikli_isaret"),
    (r"yol_?ver|give_?way|yield", "giveway"),
    (r"(^|_)dur($|_)|^stop", "stop"),
    (r"u_?donus|u_?turn|ban_turn_u|no_u($|_)", "nouturn"),
    (r"saga_?donulmez|sag_donus_yasak|no_?right_?turn|ban_turn_right", "donotturnright"),
    (r"sola_?donulmez|sol_donus_yasak|no_?left_?turn|ban_turn_left", "donotturnleft"),
    (r"ileri_?ve_?saga|ileri_?saga|ilerisag|ilerden_saga|ahead_?or_?right|straight_?or_?right|right_or_straight", "ileri_saga"),
    (r"ileri_?ve_?sola|ileri_?sola|ilerisol|ilerden_sola|ahead_?or_?left|straight_?or_?left|left_or_straight", "ileri_sola"),
    (r"sagdan|keep_?right", "keepright"),
    (r"soldan|keep_?left", "keepleft"),
    (r"hiz|speed|azami|limit|(\d)km|^\d+$", "<hiz>"),  # sayıya göre (okul bölgesi 30 da speed30, v9 ile aynı)
    (r"okul|school|child", "schoolpassing"),
    (r"devamli|continuous|double|s_viraj|zigzag", "devamli_viraj"),
    (r"yon_levha|sevron|chevron", "keskin_viraj"),
    (r"(saga|sag|right).*(viraj|curve|bend)|(viraj|curve|bend).*(saga|sag|right)", "dangerousright"),
    (r"(sola|sol|left).*(viraj|curve|bend)|(viraj|curve|bend).*(sola|sol|left)", "dangerousleft"),
    (r"saga_?mecburi|sag_?mecburi|^saga?$|turn_?right|go_?right|saga_?don", "saga_mecburi"),
    (r"sola_?mecburi|sol_?mecburi|^sola?$|turn_?left|go_?left|sola_?don", "sola_mecburi"),
    (r"ileri_?mecburi|duz_?ileri|^ileri$|ahead_only|straight_only|go_straight", "ileri_mecburi"),
    (r"b_?14|yaya.*(bilgi|mavi|info)|pedestrian.*info", "pedestrian_info"),
    (r"yaya.*(uyari|ucgen|risk)|pedestrian.*(risk|warning)", "pedestrian_risk"),
    (r"yaya|crosswalk|pedestrian|zebra", YAYA),
    (r"kasis|bump|hump", "kasis"),
    (r"kaygan|slippery", "kaygan_yol"),
    (r"calisma|road_?work|men_?at_?work|construction", "yol_calismasi"),
    (r"daralan|narrow", "daralan_yol"),
    (r"egim|(^|_)inis|(^|_)cikis|steep|slope|grade|descent", "dik_egim"),
    (r"dusen|kaya|tas_?dus|falling|rock", "dusen_kaya"),
    (r"hayvan|animal|deer|cattle|geyik", "hayvan"),
    (r"sollama|gecme_?yasak|overtak|passing", "sollama_yasak"),
    (r"ana_?yol|priority", "priorityroad"),
    (r"giris|no_?entry|girilmez|do_?not_?enter", "noentry"),
    (r"dikkat|caution|^danger$|general", "caution"),
    (r"diger|other", DIGER),
]
TR = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def norm(ad):
    return re.sub(r"[^a-z0-9]+", "_", str(ad).replace("İ", "i").lower().translate(TR)).strip("_")


def hedef(ad, siniflar):
    n = norm(ad)
    if n in siniflar:
        return n
    for desen, h in KURALLAR:
        if re.search(desen, n):
            if h == "<hiz>":
                sayi = [int(s) for s in re.findall(r"\d+", n) if int(s) % 10 == 0 and 10 <= int(s) <= 140]
                return HIZ.get(sayi[-1], DIGER) if sayi else ATLA
            return h
    return ATLA


def oto_esleme(adlar, siniflar):
    esleme, at, atla = {}, [], []
    for a in adlar:
        h = hedef(a, siniflar)
        if h == AT:
            at.append(a)
        elif h == ATLA:
            atla.append(a)
        else:
            esleme[a] = h
    return esleme, at, atla


if __name__ == "__main__":  # öz denetim: elle yapılmış Erzurum ve TTSD eşlemeleriyle aynı sonucu vermeli
    import json
    from pathlib import Path

    import yaml
    M = Path(__file__).resolve().parents[1]
    siniflar = yaml.safe_load((M / "data" / "levha640" / "data_v14.yaml").read_text(encoding="utf-8"))["names"]
    erz = yaml.safe_load((M / "data" / "dis" / "trafik_levhalari" / "data.yaml").read_text(encoding="utf-8"))["names"]
    elle = json.loads((M / "scripts" / "esleme_trafik_levhalari_v14.json").read_text(encoding="utf-8"))
    elle |= json.loads((M / "scripts" / "esleme_ttsd_v14.json").read_text(encoding="utf-8"))
    adlar = erz + list(json.loads((M / "scripts" / "esleme_ttsd_v14.json").read_text(encoding="utf-8")))
    farkli = {a: (hedef(a, siniflar), elle.get(a, DIGER)) for a in adlar if hedef(a, siniflar) != elle.get(a, DIGER)}
    assert not farkli, farkli
    ornek = {"20": "speed20", "parkyasak": "park_yasak", "park": "park_yeri", "kirmizi": AT, "sag": "saga_mecburi",
             "sagadonulmez": "donotturnright", "ilerisol": "ileri_sola", "girisyok": "noentry", "crosswalk": YAYA,
             "continuous_left": "devamli_viraj", "curve_left_dangerous": "dangerousleft", "notrucks": DIGER,
             "noovertake": "sollama_yasak", "junction": "crossroads", "b14a_yaya_gecidi": "pedestrian_info",
             "p2_durak_ve_park_yasak": "nostopping", "t12_okul_gecidi": "schoolpassing", "donel_kavsak": ATLA,
             "Hız Sınırı 50": "speed50", "bilinmeyen_sey": ATLA, "dangerousleft": "dangerousleft", "Dur": "stop"}
    yanlis = {a: (hedef(a, siniflar), b) for a, b in ornek.items() if hedef(a, siniflar) != b}
    assert not yanlis, yanlis
    print("oto_esleme öz denetim tamam:", len(adlar) + len(ornek), "ad")
