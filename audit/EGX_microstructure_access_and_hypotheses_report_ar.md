# تقرير تحقيق بيانات Microstructure وفرضيات Execution Overlay لـ EGX-Genom

**التاريخ:** 14 أغسطس 2026

## الملخص التنفيذي

تم تنفيذ المسارات الثلاثة المطلوبة: التحقق من مصدر البيانات الأصلي، فحص طرق الحصول على نسخة مجانية أو بحثية، والبحث عن فرضيات أحدث قابلة للاختبار. النتيجة الأساسية هي أن بيانات الدراسة الأصلية **ليست منشورة للتنزيل العام**، لكن الورقة تنص صراحة على أن البيانات متاحة عند الطلب من المؤلفين. لذلك فإن أفضل مسار مجاني موثق هو طلب نسخة بحثية من المؤلفين، مع إرسال طلب موازٍ محدود إلى البورصة المصرية على `info@egx.com.eg` للحصول على إذن بحثي أو إحالة إلى الجهة المالكة للبيانات.

لم يتم اختبار الفرضيات على عوائد يومية أو بيانات بديلة؛ لأن ذلك سيكون اختبارًا غير صالح لفرضيات Order Book. كما لم يتم إدخال أي إشارة Microstructure في Fair Value أو Opportunity Score. السبب أن بيانات Order File وTransaction File الأصلية غير متاحة حاليًا داخل المشروع، وأي نتيجة خلاف ذلك ستكون مصطنعة أو عرضة لتحيز القياس.

## 1. ما الذي تم التحقق منه في الورقة الأصلية؟

توضح دراسة Rushdy وSamak المنشورة في 2025 أنها حصلت على ثلاث مجموعات بيانات من EGX Information Center تغطي 123 يوم تداول من أغسطس 2017 إلى يناير 2018 لمكونات EGX30: Trade File وTransaction File وOrder File [1]. وتشير الدراسة إلى نحو 18,324 ملاحظة في Trade File، ونحو 1.74 مليون معاملة في Transaction File، ونحو 9.46 مليون ملاحظة تمثل قرابة 2.8 مليون أمر في Order File. كما أعاد الباحثان بناء Quote File على فواصل خمس دقائق من ملف الأوامر [1].

الـ Order File يتضمن، وفق نص الورقة، معرف الأمر وISIN والتوقيت واتجاه الأمر وسعر الحد والحجم وحالة التنفيذ ووقت الصلاحية وإجراء X-Stream. وهذه البنية كافية مبدئيًا لاختبار imbalance والإلغاء والتنفيذ وإعادة تكوين عمق السوق، بشرط مطابقة الأوامر بالتنفيذات، وضبط المنطقة الزمنية، ومعالجة التعديلات والإلغاءات وأحداث الشركات.

بيان توافر البيانات في الورقة واضح:

> Dataset available on request from the authors. [1]

لم يظهر في نص الورقة رابط تنزيل عام، أو مستودع raw data، أو مستودع transformed data، أو repository للكود والبيانات. لذلك لا يوجد دليل على أن البيانات متاحة للعامة دون طلب.

## 2. أفضل مسار مجاني موثق

أفضل طريق هو التواصل المباشر مع المؤلفين، لا استخدام مصدر تجاري. صفحة جامعة الجلالة الرسمية تدرج Nagwa Samak كعميدة كلية العلوم الإدارية وأستاذة الاقتصاد، وتوفر البريد `nagwa.samak@gu.edu.eg` [2]. صفحة الورقة الرسمية تدرج Ahmed Rushdy كمؤلف مراسل في كلية الاقتصاد والعلوم السياسية بجامعة القاهرة، وتوفر `ahmed_rushdy2016@feps.edu.eg` وORCID `0000-0002-9718-148X` [1].

المطلوب في الرسالة ليس طلب حقوق إعادة التوزيع، بل نسخة خاصة للاستخدام البحثي غير التجاري، أو نسخة مشتقة/مجهولة الهوية، أو Quote File يعاد بناؤه، مع قبول شروط التخزين وعدم النشر. يجب طلب حق التخزين المحلي والتحليل الحاسوبي وإنتاج النتائج المجمعة فقط.

قناة EGX الرسمية العامة هي `info@egx.com.eg`، ويعرض الموقع رقم الخط الساخن 15221 [3]. لم تُظهر صفحات EGX العامة التي تمت مراجعتها مسارًا منشورًا لطلب مجاني لملفات Order/Transaction التاريخية. كما يوضح إخلاء المسؤولية أن مواد EGX مملوكة للبورصة، وأن التخزين الإلكتروني والنسخ وإنشاء الأعمال المشتقة تحتاج إلى إذن كتابي [4]. لذلك يجب أن يتضمن أي رد من EGX إذنًا صريحًا للاستخدام البحثي المحلي.

## 3. هل توجد بدائل مفتوحة؟

مستودع LOBFrame مفتوح المصدر ويوفر معالجة وتدريبًا وتقييمًا واختبارات backtest لبيانات LOB، لكنه لا يوفر بيانات EGX. وهو يتوقع بيانات بصيغة LOBSTER، بينما ملفات EGX المشار إليها في الورقة تحتاج إلى محول مستقل من بنية EGX إلى schema موحدة [5]. كما أن ترخيصه CC BY-NC-ND 4.0، ولذلك يجب إجراء مراجعة ترخيص قبل إدخال أي جزء منه في المنتج [5].

تؤكد صفحة ICE الرسمية أن بيانات EGX من نوع Market-by-Order وLevel 2 وبيانات تاريخية tick-by-tick موجودة تجاريًا [6]. هذا يثبت قابلية التنفيذ التقنية، لكنه ليس مسارًا مجانيًا، ولذلك لا يُعتمد ولا يُوصى بشرائه ضمن هذا التحقيق.

## 4. تقييم الفرضيات الأصلية

| الفرضية | القرار | القيمة المحتملة لـ EGX-Genom | البيانات المطلوبة |
|---|---|---|---|
| Order-flow imbalance يتنبأ بالحركة القصيرة | تُختبر أولًا | إشارة توقيت قصيرة الأجل | Order + Transaction + Trade |
| Absorption | تُختبر بشروط | تمييز امتصاص السيولة من الحركة العابرة | Trades + depth + timestamps |
| Liquidity sweep ثم reversal | تُختبر | تحذير تنفيذ ومخاطر انعكاس | LOB متعدد المستويات + trades |
| Liquidity vacuum | أولوية مرتفعة | كشف هشاشة السيولة قبل توسع الحركة | depth + cancellations + volatility |
| Order-book imbalance يتنبأ بالعائد | تُختبر، لكن ليست Fair Value | Flow overlay | LOB snapshots/events |
| Cancellation intensity | تُختبر بحذر | قياس جودة السيولة المؤقتة | Order lifecycle كامل |
| Execution probability | أولوية مرتفعة | تقدير احتمال تنفيذ أمر فعلي | Queue/order IDs + trades |
| Liquidity replenishment | تُختبر | قياس resiliency بعد التنفيذات العدوانية | Order + transaction |
| Price-impact asymmetry | أولوية مرتفعة | تقدير الانزلاق وحجم المركز | trades + depth + side |
| Large-order behavior حول الاختراق | تُختبر لاحقًا | وصف سلوكي وتنفيذي | size-normalized orders + event windows |
| Repeated placement/cancellation | مرحلة ثانية | قد تكشف ضوضاء أو أنماطًا متكررة | order IDs + lifecycle |
| Retail-trapping signatures | لا تُجعل هدفًا رئيسيًا | لا تثبت هوية أو نية المشاركين | لا تُفسر دون دليل مباشر |

## 5. الفرضيات الأحدث التي أضيفت بعد البحث

### 5.1 قابلية التنفيذ أهم من دقة التنبؤ
دراسة LOBFrame الحديثة تحذر من أن accuracy أو AUC قد لا تعني إشارة قابلة للتنفيذ، وتقترح قياس احتمال تنفيذ معاملة صحيحة وصافي الأداء بعد التكلفة [7]. هذه فرضية مهمة جدًا للمشروع:

> الإشارة لا تُقبل كإشارة تنفيذ إلا إذا حسنت احتمال تنفيذ قرار صحيح بعد السبريد والانزلاق والقيود العملية.

هذه الفرضية مناسبة لتصميم Execution Overlay وليست مناسبة لإضافة نموذج Fair Value.

### 5.2 تفاعل imbalance مع ضغط السيولة
توضح مذكرة Federal Reserve لعام 2025 أن أثر تدفق الأوامر الاتجاهي يكبر عندما ينخفض عمق السوق وتزداد التقلبات [8]. الفرضية الأفضل ليست `imbalance → return` فقط، بل:

> `Order-flow imbalance × low depth × high volatility` يفسر ضغطًا سعريًا أكبر من imbalance في ظروف السيولة الطبيعية.

هذه صياغة أحدث وأكثر فائدة لاتخاذ قرار حجم المركز والتوقيت.

### 5.3 تصفية الأوامر العابرة قبل حساب OBI
تقدم دراسة 2025 طريقة لتصفية الأحداث حسب عمر الأمر وعدد التحديثات والفاصل بين التحديثات، ثم مقارنة OBI المصفى بـ OBI الخام [9]. وتؤكد ضرورة فصل الارتباط المعاصر عن الاختبار السببي. الفرضية المقترحة:

> OBI المصفى من الأوامر العابرة يعطي إشارة أكثر استقرارًا من OBI الخام، لكن يجب قبولها فقط إذا تحسن net-of-cost execution وليس correlation فقط.

### 5.4 نظامان مختلفان لتأثير Tick Size
توضح دراسة عن Tick Size وPrice Reversal أن أثر tick size قد يكون augmentation أو censoring حسب معدل كون tick size binding وحسب spread وdepth والسيولة [10]. وهذا مهم للـEGX لأن الدراسة الأصلية تذكر حدًا موحدًا قدره EGP 0.01 خلال فترة العينة [1].

## 6. ما الذي تم اختباره فعليًا؟

تم اختبار **قابلية البيانات والمنهج**، وليس العوائد الميكروهيكلية نفسها. السبب أن المشروع لا يملك حاليًا Order File وTransaction File وLOB snapshots أصلية. اختُبرت الفرضيات التالية من حيث إمكانية القياس ومخاطر التحيز:

| الاختبار | النتيجة |
|---|---|
| استخدام الأسعار اليومية بدل Order File | مرفوض؛ لا يقيس LOB أو execution probability |
| إدخال OBI داخل Fair Value | مرفوض؛ يخلط الأفق القصير بالقيمة الأساسية |
| استخدام LOBFrame كبيانات | مرفوض؛ المستودع يوفر كودًا فقط لا EGX data |
| استخدام ICE كمسار مجاني | مرفوض؛ الصفحة تثبت أنه منتج بيانات تجاري |
| اختبار accuracy فقط | مرفوض؛ لا يثبت قابلية التنفيذ |
| اختبار OBI الخام دون تصفية | غير كافٍ؛ معرض لضوضاء الأوامر العابرة |
| اختبار imbalance مع depth وvolatility | مقبول كفرضية رئيسية عند وصول البيانات |
| اختبار execution probability بعد التكلفة | مقبول كاختبار قبول نهائي للإشارة |

وبالتالي لم يتم اختلاق نتائج حول وجود alpha أو وجود trapping أو manipulation في EGX.

## 7. التصميم الصحيح داخل EGX-Genom

إذا وصلت البيانات، تُضاف طبقة مستقلة باسم `Execution Overlay`، ولا تعدل Fair Value أو ترتيب القيمة الأساسية. مخرجاتها المقترحة هي `Liquidity Score` و`Execution Risk` و`Price Impact Estimate` و`Flow Signal` و`Liquidity Stress Flag`. يمكن للطبقة أن تعدل **التوقيت وحجم المركز وطريقة التنفيذ** فقط، ولا تحول سهمًا Fundamental ضعيفًا إلى Buy.

بوابة قبول الإشارة يجب أن تتطلب walk-forward زمنيًا، فصل التدريب عن الاختبار، تكلفة spread وslippage، اختبارًا عبر الأسهم لا على سهم واحد، ومقارنة بالإشارة الخام والمصفاة. ويجب تسجيل مصدر كل حقل وتوقيت ظهوره، مع رفض أي feature لم يكن متاحًا قبل لحظة القرار.

## 8. الإجراء التالي الدقيق

الإجراء الأول: إرسال الطلب إلى Ahmed Rushdy وNagwa Samak وطلب نسخة بحثية من البيانات أو نسخة مشتقة آمنة. الإجراء الثاني: إرسال طلب موازي إلى `info@egx.com.eg` يسأل عن برنامج research-access مجاني أو إحالة إلى EGX Information Center. الإجراء الثالث: عدم تعديل محرك EGX-Genom حتى تصل البيانات أو رد مكتوب يثبت نطاق الاستخدام.

لا توجد حاليًا **نسخة مجانية عامة قابلة للتنزيل تم التحقق منها**. المسار المجاني الموثق هو author-request، مع EGX كمسار مؤسسي موازٍ.

## 9. مسودة البريد الإنجليزي

**Subject:** Request for a non-commercial research copy of EGX order and transaction data

Dear Dr. Rushdy and Professor Samak,

I am conducting independent, non-commercial quantitative research on market microstructure and execution risk in the Egyptian Exchange. I read your 2025 paper, “Examining Market Quality on the Egyptian Exchange (EGX): An Intraday Liquidity Analysis,” and noted the statement that the underlying dataset is available on request from the authors.

I would be grateful if you could advise whether it would be possible to receive a private research copy of the historical data used in the study, covering the 123 trading days from August 2017 to January 2018. Ideally, this would include the Trade File, Transaction File, and Order File. If the raw files cannot be shared, a de-identified or derived research-safe version would also be very useful, including reconstructed five-minute quotes, bid/ask depth, order direction, cancellations, and execution information.

The intended use is strictly non-commercial research. We would store the files privately, use them only for computational analysis, and publish only aggregated findings without redistributing raw records or attempting to identify any participant. We are not affiliated with Cairo University or Galala University, and we would comply with any data-use, confidentiality, citation, or deletion requirements you specify.

The research questions concern measurable liquidity and execution effects, including order-flow imbalance under depth stress, liquidity replenishment, cancellation intensity, execution probability, price impact, and the practical performance of filtered versus unfiltered order-book signals. We will not infer participant identity or intent from the data.

If you are unable to share the raw data, I would appreciate any guidance on whether a derived file, reconstructed quote file, institutional repository, or official EGX research-access route is available.

Thank you for your time and for the valuable contribution of your study.

Kind regards,

[Full Name]
[Email Address]
[Project/GitHub URL, if appropriate]

## References

[1]: https://www.mdpi.com/1911-8074/18/1/32 "Rushdy & Samak (2025), Examining Market Quality on the Egyptian Exchange"
[2]: https://www.gu.edu.eg/personnel/nagwa-abdullah-abdul-aziz-samak/ "Galala University official profile: Nagwa Samak"
[3]: https://www.egx.com.eg/en/contact.aspx "Egyptian Exchange official contact page"
[4]: https://www.egx.com.eg/en/Disclamer.aspx "Egyptian Exchange official disclaimer"
[5]: https://github.com/FinancialComputingUCL/LOBFrame "LOBFrame open-source repository"
[6]: https://developer.ice.com/fixed-income-data-services/catalog/egyptian-exchange-egx "ICE Egyptian Exchange data catalog"
[7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/ "Briola, Bartolucci & Aste (2025), Deep limit order book forecasting"
[8]: https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html "Federal Reserve (2025), Order Flow Imbalances and Amplification of Price Movements"
[9]: https://arxiv.org/html/2507.22712v1 "Anantha, Jain & Maiti (2025), Order Book Filtration and Directional Signal Extraction"
[10]: https://www.mdpi.com/2227-7072/9/2/19 "Sirnes & Dinh (2021), Tick Size and Price Reversal after Order Imbalance"
