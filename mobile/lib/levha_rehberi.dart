// Levha rehberi: her sınıfın anlamı, neyle karışabileceği ve uygulamanın ne söylediği.
// Çizimler Wikimedia Commons'taki resmî KGM levha çizimleri (assets/levhalar/<sınıf>.png; CC BY-SA 4.0 / CC0 / kamu malı,
// yazarlar Ayarlar'da). Erzurum setine özgü 4 levhanın (refüj başı...) çizimi yok, simge gösterilir.
import 'package:flutter/material.dart';

import 'alerts.dart';

/// sınıf -> (anlamı, neyle karışabilir / not). Sıra kataloğun sırası.
const signInfo = <String, ({String anlam, String not})>{
  'stop': (anlam: 'Kavşağa girmeden tamamen dur, yol ver.', not: ''),
  'noentry': (anlam: 'Bu yöne taşıt girişi yasak (tek yönlü yolun çıkışı).', not: 'Düz kırmızı halka "taşıt trafiğine kapalı" ile karışır.'),
  'giveway': (anlam: 'Ana yoldaki araçlara yol ver, gerekirse dur.', not: ''),
  'schoolpassing': (anlam: 'Okul geçidi: çocuklar yola çıkabilir, yavaşla.', not: 'Yaya geçidi üçgeniyle karışır (iki çocuk figürü).'),
  'pedestrian_risk': (anlam: 'İleride yaya geçidi; yavaşla, yayaya yol ver.', not: 'Okul geçidiyle karışır. 4,80 m yükseklik levhası bu değildir.'),
  'dangerousleft': (anlam: 'Sola tehlikeli viraj; hız düşür.', not: 'Uzaktaki okunmayan üçgenler buna benzer.'),
  'dangerousright': (anlam: 'Sağa tehlikeli viraj; hız düşür.', not: 'Düşen kaya üçgeniyle karışabilir.'),
  'crossroads': (anlam: 'Kontrolsüz kavşak; sağdan gelene yol ver.', not: 'Yandan yol katılımı (T-22) ve düşen kaya üçgenleriyle karışır.'),
  'caution': (anlam: 'Belirtilmemiş tehlike; altındaki plaka açıklar.', not: 'Şevron (viraj yön levhası) bu değildir.'),
  'donotturnleft': (anlam: 'Sola dönüş yasak.', not: ''),
  'donotturnright': (anlam: 'Sağa dönüş yasak.', not: ''),
  'nouturn': (anlam: 'U dönüşü yasak.', not: ''),
  'keepleft': (anlam: 'Engelin / refüjün solundan geç.', not: ''),
  'keepright': (anlam: 'Engelin / refüjün sağından geç.', not: ''),
  'speed30': (anlam: 'Azami hız 30 km/sa.', not: 'Uzakta 30/50/80 rakamları karışır; sarı zeminlisi yol çalışmasında geçici sınır.'),
  'speed50': (anlam: 'Azami hız 50 km/sa.', not: 'Sarı zeminlisi geçici sınır (yol çalışması).'),
  'speed70': (anlam: 'Azami hız 70 km/sa.', not: ''),
  'nostopping': (anlam: 'Duraklamak ve park etmek yasak (kırmızı çarpı).', not: 'Tek çizgili "park etmek yasak" ile karışır.'),
  'priorityroad': (anlam: 'Ana yol: kavşaklarda geçiş üstünlüğü sende.', not: 'Çizgili olanı "ana yol sonu"dur.'),
  'pedestrian_info': (anlam: 'Yaya geçidi tam burada (mavi kare).', not: 'Üçgen olanı uyarı levhasıdır.'),
  'kasis': (anlam: 'Yolda tümsek; yavaşla.', not: ''),
  'durak': (anlam: 'Otobüs / dolmuş durağı; durağın 15 m içinde durma.', not: 'Mavi "D" levhası demiryolu değildir.'),
  'demiryolu': (anlam: 'Hemzemin demiryolu geçidi (bariyerli veya bariyersiz): dur, bak, geç.', not: 'Çarpı biçimli olanı geçidin tam önündedir.'),
  'refuj_basi': (anlam: 'Yol ortasındaki adanın (refüjün) başı; belirtilen taraftan geç.', not: 'Erzurum setine özgü; modelde "bilinmeyen levha" sayılır.'),
  'donus_adasi': (anlam: 'Dönüş adası; adanın etrafından dön.', not: 'Erzurum setine özgü; modelde "bilinmeyen levha" sayılır.'),
  'ileri_saga': (anlam: 'İleri veya sağa mecburi yön.', not: 'Modelde "bilinmeyen levha" sayılır.'),
  'ileri_sola': (anlam: 'İleri veya sola mecburi yön.', not: 'Modelde "bilinmeyen levha" sayılır.'),
  'ada_etrafinda': (anlam: 'Dönel kavşak: ada etrafında dön, adadakine yol ver.', not: ''),
  'isikli_isaret': (anlam: 'İleride trafik ışığı var.', not: ''),
  'keskin_viraj': (anlam: 'Viraj yön levhası (şevron): ok yönünde dön, hız düşür.', not: 'Kırmızı-beyaz ya da sarı-siyah olabilir.'),
  'devamli_viraj': (anlam: 'Art arda virajlar (S viraj).', not: 'Tek viraj levhası ve yön tabelalarıyla karışır.'),
  'sollama_yasak': (anlam: 'Öndeki taşıtı geçmek yasak.', not: ''),
  'dusen_kaya': (anlam: 'Yamaçtan taş düşebilir.', not: 'Kavşak üçgeniyle karışır.'),
  'hayvan': (anlam: 'Ehli veya vahşi hayvan yola çıkabilir.', not: ''),
  'daralan_yol': (anlam: 'Kaplama daralıyor.', not: 'İki yönlü trafik levhası bu değildir.'),
  'dik_egim': (anlam: 'Tehlikeli iniş veya çıkış (yüzde eğim).', not: ''),
  'speed40': (anlam: 'Azami hız 40 km/sa.', not: '4,80 m yükseklik sınırı levhası bu değildir.'),
  'speed60': (anlam: 'Azami hız 60 km/sa.', not: ''),
  'hiz_sonu': (anlam: 'Hız sınırı sonu; genel sınır geçerli.', not: 'Gri çizgili daire.'),
  'yol_calismasi': (anlam: 'Yolda çalışma; işçiler ve geçici hız sınırı.', not: 'Genelde sarı zeminli.'),
  'kaygan_yol': (anlam: 'Islak veya buzlu kaygan zemin.', not: ''),
};

const otherInfo = (anlam: 'Model levha olduğunu anladı ama bu listede yok: yön tabelası, yükseklik sınırı, bilgi levhaları.', not: 'Ekranda gösterilir, seslendirilmez.');

class SignGuideScreen extends StatelessWidget {
  const SignGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final names = [...signs.keys, otherSign];
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: names.length,
      itemBuilder: (context, i) {
        final n = names[i];
        final info = n == otherSign ? otherInfo : (signInfo[n] ?? (anlam: '', not: ''));
        final says = n == otherSign ? 'Sesli uyarı yok' : 'Uygulama: "${signs[n]!.text}"';
        return Card(
          child: ListTile(
            leading: SizedBox(
              width: 56,
              height: 56,
              child: Image.asset('assets/levhalar/$n.png', errorBuilder: (_, _, _) => const Icon(Icons.signpost, size: 40)),
            ),
            title: Text(label(n)),
            subtitle: Text([info.anlam, if (info.not.isNotEmpty) info.not, says].join('\n')),
            isThreeLine: true,
          ),
        );
      },
    );
  }
}
