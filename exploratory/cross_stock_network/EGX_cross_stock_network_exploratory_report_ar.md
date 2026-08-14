# تقرير استكشافي: علاقات الأسهم المتقاطعة وشبكات السيولة في EGX

**الحالة:** Exploratory Research Only

**تاريخ التشغيل:** 14 أغسطس 2026

**المشروع:** EGX-Genom

## الخلاصة التنفيذية

تم فحص مجموعتي البيانات المذكورتين في الطلب، Shaban وAl-Refaey، ثم بُني مسار بحثي مستقل لا يغير محرك Fair Value أو Opportunity Ranking أو التوصيات الإنتاجية. تم اختبار علاقات lead-lag في العوائد، ومؤشرات السيولة المشتقة من OHLCV، والتقلب، والحجم غير الاعتيادي، والمدى السعري. استُخدمت ضوابط للسوق والعائد الذاتي، وتصحيح Benjamini–Hochberg لتعدد الاختبارات، وتقسيم زمني لاختبار الاستقرار، ثم أضيفت اختبارات network concentration وclustering وnull randomization.

النتيجة الأساسية هي أن البيانات تسمح باكتشاف **أنماط ارتباط وسلوك متقاطع**، لكنها لا تكفي لإثبات alpha استثماري قابل للتنفيذ أو لإثبات هوية المشاركين أو نيتهم. لذلك لم تُدخل أي إشارة في Fair Value، ولم تُغيّر أي توصية إنتاجية، ولم يُسمح لأي نتيجة بأن تحول سهمًا Fundamental ضعيفًا إلى Buy.

> القرار: تُحفظ هذه الوحدة كمسار بحثي مستقل. لا تُرقّى إلى Execution Overlay إلا بعد اختبار out-of-sample حقيقي على بيانات مؤرخة قابلة للتنفيذ، ويفضل بعد الحصول على Quote/Trade أو Order-level data.

## مصادر البيانات وprovenance

| المصدر | التغطية الخام | ملفات الأسهم المستخدمة | الفترة المرصودة | الحقول الأساسية | SHA-256 للملف المضغوط |
|---|---:|---:|---|---|---|
| Eyad Shaban – Kaggle | 267 CSV | 254 سهمًا بعد استبعاد مؤشرات EGX | 2000-01-02 إلى 2023-12-12 | Date, Price, Open, High, Low, Vol., Change % | `dcf31606c1b61801e7d5f7bf1af34274184c0e660c86a0fd1210eeda03391b06` |
| Mahmoud Al-Refaey – Kaggle | 198 ملف أسهم + ملفي metadata | 198 سهمًا | 2021-01-03 إلى 2026-02-04 | Date, Open, High, Low, Close, Volume, Dividends, Stock Splits | `8ca158b01a7016d690b99573a8933422a9de42553e15e06b2165dff32da29c5c` |

تم استبعاد `EGX 30` و`EGX 30 Capped` و`EGX 70 EWI` و`EGX 100` و`EGX 100 EWI` من Shaban؛ لأنها مؤشرات وليست أسهمًا، وإدخالها داخل شبكة الأسهم كان سيخلق علاقات ميكانيكية ومصطنعة. لم توجد تواريخ مكررة في جرد المصدرين، وتم تسجيل الجرد التفصيلي في `source_inventory.json`.

## بروتوكول الاختبار

تم توحيد التاريخ والسعر والحجم مع احترام اختلاف schema بين المصدرين. استُخدم العائد اللوغاريتمي اليومي. كما حُسبت مؤشرات وصفية فقط: Amihud-like illiquidity proxy من `|return| / traded value`، تقلب متحرك 20 يومًا، abnormal volume من الحجم إلى median متحرك 20 يومًا، والمدى السعري النسبي.

لكل علاقة موجهة `leader → follower` وللـ lags التالية: 1 و2 و3 و5 أيام، تم تقدير العلاقة بعد التحكم في عائد السهم التابع المتأخر وعائد السوق الحالي والمتأخر. لم يتم تفسير هذه العلاقات كسببية؛ هي اختبارات lead-lag استكشافية. تم إجراء BH-FDR على مجموعة الاختبارات لكل مصدر ومقياس، ثم أُعيد اختبار العلاقات المكتشفة على الجزء الزمني اللاحق. لا تُعد العلاقة مستقرة إلا إذا حافظت على الإشارة ونجحت في الجزء اللاحق.

## نتائج الاختبارات

| المصدر | المقياس | اختبارات الأزواج/lag | دلالة خام | دلالة بعد FDR | مستقرة زمنيًا |
|---|---|---:|---:|---:|---:|
| Shaban | Return | 245,153 | 68,688 | 40,000 | 37,714 |
| Shaban | Illiquidity proxy | 245,184 | 149,758 | 140,351 | 130,831 |
| Shaban | Volatility | 244,871 | 32,158 | 3,272 | 3,200 |
| Shaban | Abnormal volume | 238,387 | 31,961 | 4,291 | 4,200 |
| Shaban | Range | 245,199 | 87,386 | 63,718 | 59,093 |
| Al-Refaey | Return | 153,009 | 9,135 | 507 | 429 |
| Al-Refaey | Illiquidity proxy | 152,418 | 57,275 | 43,064 | 23,659 |
| Al-Refaey | Volatility | 153,590 | 16,506 | 1,807 | 1,641 |
| Al-Refaey | Abnormal volume | 141,925 | 15,028 | 152 | 137 |
| Al-Refaey | Range | 152,604 | 42,043 | 21,862 | 17,793 |

الأرقام الكبيرة في Shaban، خصوصًا في illiquidity وrange، لا تعني وجود 130 ألف فرصة تداول. فهي علاقات اختبارية متداخلة، ويُحتمل أن تعكس عوامل سوقية أو قيودًا في OHLCV أو persistence في المتغيرات. لذلك استُخدمت كأداة تشخيص وليس كقائمة إشارات قابلة للتداول.

## التحقق بين المصدرين

| المقياس | علاقات Shaban المستقرة | علاقات Al-Refaey المستقرة | نفس القائد والتابع والـ lag والاتجاه | معدل التكرار مقابل المصدر الأصغر |
|---|---:|---:|---:|---:|
| Return | 37,714 | 429 | 27 | 6.3% |
| Illiquidity | 130,831 | 23,659 | 13,571 | 57.4% |
| Volatility | 3,200 | 1,641 | 14 | 0.9% |
| Abnormal volume | 4,200 | 137 | 6 | 4.4% |
| Range | 59,093 | 17,793 | 7,217 | 40.6% |

التكرار المنخفض للعوائد والتقلب والحجم يمنع ترقية تلك الإشارات إلى Signal إنتاجية. التكرار الأعلى في illiquidity وrange يبرر بحثًا إضافيًا، لكنه لا يثبت قابلية التنفيذ أو السببية، لأن كلا المقياسين مشتق من OHLCV وقد يتأثران بنفس عوامل السوق.

## الشبكات والـ null models

تم بناء شبكة موجهة من العلاقات التي اجتازت FDR والتحقق الزمني. استُخدم null model مستقل يوزع counterpart عشوائيًا على عقد الشبكة بدل إعادة توزيع follower labels بالطريقة التي تحفظ درجة الدخول وتنتج p-value غير مفيدة.

| المصدر / المقياس | الحواف المستقرة | أقصى in-degree مرصود | متوسط null | p-value الاستكشافية للتركيز |
|---|---:|---:|---:|---:|
| Shaban / Return | 37,714 | 263 | 184.6 | 0.005 |
| Shaban / Illiquidity | 130,831 | 729 | 581.8 | 0.005 |
| Shaban / Volatility | 3,200 | 70 | 24.1 | 0.005 |
| Shaban / Abnormal volume | 4,200 | 85 | 30.2 | 0.005 |
| Shaban / Range | 59,093 | 550 | 278.2 | 0.005 |
| Al-Refaey / Return | 429 | 20 | 7.725 | 0.005 |
| Al-Refaey / Illiquidity | 23,659 | 346 | 152.3 | 0.005 |
| Al-Refaey / Volatility | 1,641 | 45 | 17.895 | 0.005 |
| Al-Refaey / Abnormal volume | 137 | 10 | 4.77 | 0.005 |
| Al-Refaey / Range | 17,793 | 287 | 119.87 | 0.005 |

هذه النتيجة تعني أن العلاقات ليست موزعة عشوائيًا وفق هذا null البسيط، لكنها لا تكفي لتحديد مصدر التأثير أو بناء محفظة. يلزم null أقوى يحافظ على calendar effects وcross-sectional activity وsector membership المؤرخة قبل أي claim استثماري.

## Clustering وpropagation

تم بناء clustering سلوكي من سبع ميزات وصفية في Shaban وست ميزات في Al-Refaey، باستخدام discovery period فقط لبناء المجموعات. أُسندت بيانات الفترة اللاحقة إلى أقرب centroid دون إعادة تدريب المستقبل. لم تتوفر sector membership مؤرخة، ولذلك لم تُستخدم القطاعات كـ control.

| المصدر | cutoff الاكتشاف | عدد المجموعات | ثبات المجموعة التقريبي | المقاييس التي تجاوزت null داخل المجموعة |
|---|---|---:|---:|---|
| Shaban | 2014-03-30 | 42 | 38.3% dominant assignment | Return, Illiquidity, Abnormal volume, Range |
| Al-Refaey | 2023-05-01 | 21 | 52.6% dominant assignment | Illiquidity, Volatility, Abnormal volume, Range |

هذه النتيجة **استكشافية فقط**. ضعف ثبات مجموعات Shaban، واختلاف الفترات بين المصدرين، وغياب القطاعات المؤرخة، كلها تمنع الاستنتاج بأن هناك propagation قابلًا للتداول.

## فرضيات أحدث تم اختبار قابليتها

تم إدراج فرضيات أحدث من مجرد OBI التقليدي في خطة الاختبار: تصفية الأوامر العابرة قبل حساب imbalance، التفاعل بين imbalance والعمق والتقلب، قياس احتمال التنفيذ الصحيح، أثر tick-size regimes، والتمييز بين liquidity replenishment وabsorption. لم تُختبر هذه الفرضيات على بيانات مصطنعة؛ لأن البيانات المتاحة OHLCV يومية ولا تحتوي order/quote/trade-level timestamps.

النتيجة المنهجية هي أن هذه الفرضيات تستحق الاختبار عند الحصول على Order/Transaction/Quote data، لكنها لا يمكن اختبارها بنزاهة على OHLCV وحده. لم يتم استنتاج cancellation intensity أو absorption أو liquidity vacuum من نطاق اليوم؛ فهذا سيكون proxy غير مبرر.

## القرار على EGX-Genom

لم يتم تعديل أي ملف في المسار الإنتاجي. لم تتغير Fair Value أو Opportunity Score أو Market Stance أو التوصيات. الوحدة الجديدة موجودة تحت `exploratory/cross_stock_network/`، ومخرجاتها لا تدخل dashboard أو decision engine.

القرار الحالي هو **عدم الترقية** إلى Execution Overlay. يمكن ترقية النتيجة فقط بعد تحقق الشروط التالية: الحصول على بيانات Quote/Trade أو Order-level حقيقية، وجود timestamp وtimezone وcorporate-action treatment، تعريف مؤرخ للـ universe والقطاعات، pre-registration للفرضيات، holdout زمني نهائي لم يُستخدم في الاختيار، احتساب transaction costs وslippage، واختبار قابلية التنفيذ لا مجرد sign accuracy.

## ملفات إعادة الإنتاج

| الملف | الوظيفة |
|---|---|
| `inventory_sources.py` | جرد الملفات والتواريخ والتكرارات والحقول |
| `run_network_analysis.py` | lead-lag وmarket controls وBH-FDR وtemporal validation |
| `consolidate_results.py` | تجميع النتائج دون الكتابة المتعارضة بين العمليات |
| `analyze_network_structure.py` | network concentration وnull randomization وcross-source replication |
| `cluster_and_propagation.py` | clustering سلوكي وداخل/خارج المجموعة مع null permutation |
| `source_inventory.json` | provenance وتغطية المصدرين |
| `results/summary_clean.json` | ملخص المقاييس بعد استبعاد مؤشرات EGX |
| `results/network_structure_summary.json` | نتائج الشبكة والـ null models |
| `results/cluster_propagation_summary.json` | نتائج clustering وpropagation |

## المراجع

[1]: https://www.kaggle.com/datasets/eyadshaban/egx-stock-data "EGX Stock data – Eyad Shaban, Kaggle"

[2]: https://www.kaggle.com/datasets/mahmoudalrefaey/egx-egyptian-stocks-2021-2026 "EGX Egyptian Stocks Historical Data 2021–2026 – Mahmoud Al-Refaey, Kaggle"

[3]: https://www.egx.com.eg/en/homepage.aspx "The Egyptian Exchange – official website"

[4]: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx "ICE EGX data catalogue"
