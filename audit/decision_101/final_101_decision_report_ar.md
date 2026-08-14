# تقرير تشغيل صندوق EGX-Genom — EGX30 وEGX70

**تاريخ التشغيل:** 14 أغسطس 2026.  
**النطاق:** 101 سهمًا ضمن EGX30 وEGX70.  
**قاعدة القرار:** لا تُنتج توصية قابلة للتنفيذ إلا عند وجود سعر قابل للاستخدام وقيمة عادلة محسوبة من بيانات مالية حقيقية؛ وإلا تكون النتيجة `abstain`.

## الخلاصة التنفيذية

اكتملت تغطية بنود القوائم المالية على مستوى الكون بالكامل: **101/101 سهمًا**. وبعد ربط البنود بمحرك `FairValueEngine` وإجراء التحقق المحاسبي، اكتُشفت وصُححت نقطة جوهرية في الوحدات: صفحات StockAnalysis تصرح بأن القوائم المالية معروضة بـ **million EGP**، بينما EPS لكل سهم وعدد الأسهم بوحداتهما المطلقة. لذلك تم تحويل البنود المطلقة إلى EGP بضربها في 1,000,000، مع عدم تغيير EPS أو shares outstanding.

نتجت قيمة عادلة متعددة النماذج لـ **25 سهمًا** في طبقة valuation، ونتجت توصيات قابلة للتنفيذ لـ **23 سهمًا** بعد تطبيق شرط السعر الحي. أما الامتناع عن 78 سهمًا فليس فشلًا في التغطية المالية؛ بل تطبيق مقصود لقاعدة عدم تصنيع قرار عند غياب قيمة عادلة أو السعر.

## التوزيع النهائي للتوصيات

| النتيجة | العدد | النسبة من 101 | الأسهم |
|---|---:|---:|---|
| Sell | 15 | 14.9% | ABUK, ALCN, EFID, EFIH, EGAL, EHDR, FWRY, MFPC, MPCI, MPRC, MTIE, ORHD, ORWE, RACC, ZEOT |
| Strong Buy | 3 | 3.0% | ARCC, EMFD, SCEM |
| Reduce | 2 | 2.0% | AMOC, ISMQ |
| Buy | 1 | 1.0% | MCQE |
| Accumulate | 1 | 1.0% | POUL |
| Hold | 1 | 1.0% | BIOC |
| Abstain | 78 | 77.2% | 68 بلا fair value متعدد النماذج، و10 بلا سعر صالح |
| **الإجمالي** | **101** | **100%** | — |

## أفضل إشارات القيمة الحالية

| السهم | التوصية | العائد المتوقع مقابل السعر |
|---|---|---:|
| EMFD | Strong Buy | +55.6% |
| SCEM | Strong Buy | +25.8% |
| ARCC | Strong Buy | +14.0% |
| POUL | Accumulate | +7.0% |
| MCQE | Buy | +5.3% |

هذه الإشارات ليست ضمانًا للعائد، وإنما ناتج مقارنة السعر بالقيمة العادلة المحسوبة؛ وتظل خاضعة لمخاطر السوق والسيولة وجودة الإفصاح.

## نتائج اختبارات التغطية والأسعار

| الاختبار | النتيجة |
|---|---:|
| إجمالي الكون | 101/101 |
| تغطية line items المالية | 101/101 |
| أسهم لها shares outstanding من صفحة الإحصاءات | 95/101 في مسار StockAnalysis، مع بقاء الأسهم غير المتاحة في حالة امتناع |
| تاريخ سعر قابل للاستخدام | 91/101 |
| أسهم بلا سعر صالح | 10 |
| Fair value متعدد النماذج | 25/101 |
| توصيات قابلة للتنفيذ | 23/101 |
| حالات abstain النهائية | 78/101 |

الأسهم التي لم يتوفر لها سعر صالح في آخر تشغيل هي: **ACTF, AIDC, AIHC, GPIM, IEEC, KRDI, TANM, TAQA, VLMR, VLMRA**. ويجب عدم تحويلها إلى Buy/Sell/Hold حتى ينجح جامع الأسعار أو تتم مراجعة مصدر سعري بديل موثق.

## ما تم تعديله

تم إنشاء `audit/build_live_readiness.py` لبناء readiness حي من صفحات StockAnalysis، واستخراج القوائم السنوية، وعدد الأسهم من صفحة الإحصاءات، ثم تمريرها إلى `FairValueEngine`. وتم إنشاء `audit/prepare_decision_readiness.py` لمواءمة ناتج المحرك مع schema الذي يقرأه decision engine.

تم تحديث `audit/run_101_decision_test.py` بحيث يقرأ القيم العادلة المحسوبة فعليًا من readiness بدل إعادة ضبطها إلى `None`. كما تم حفظ سجلات التشغيل في `audit/decision_101/`، بما في ذلك `live_readiness.json` و`results.json` و`decision_engine_scaled.log` و`run_101_decision_test_final_v2.log`.

## التقييم المهني للحالة الحالية

النظام أصبح قادرًا على إنتاج قرارات فعلية لجزء موثق من الكون، مع تغطية مالية كاملة وامتناع صريح عن الحالات غير الكافية. لكنه **ليس 101/101 توصية قابلة للتنفيذ**، ولا ينبغي أن يكون كذلك قبل توافر قيمة عادلة متعددة النماذج وسعر حديث لكل سهم. النتيجة الصحيحة للصندوق حاليًا هي: **101/101 مغطى بحثيًا، 23/101 قابل للتنفيذ، و78/101 ممتنع حفاظًا على جودة القرار**.

الخطوة التشغيلية التالية ليست إضافة طبقات جديدة؛ بل تحسين مسارين محددين فقط: استكمال الأسعار العشرة الفاشلة، ثم استكمال نماذج القيمة العادلة للأسهم التي لديها بيانات مالية ولكنها لا تحقق شرط ثلاثة نماذج مستقلة، مع مراجعة البنوك وشركات الخدمات المالية بنماذج مناسبة مثل P/E وP/B بدلاً من DCF الصناعي.

## ملفات النتائج الرئيسية

| الملف | الاستخدام |
|---|---|
| `audit/decision_101/live_readiness.json` | نتيجة الربط الحي بين القوائم وFairValueEngine |
| `research/data/dashboard/decision_readiness.json` | مدخل decision engine |
| `research/data/dashboard/recommendations.json` | التوصيات المنتجة |
| `audit/decision_101/results.json` | اختبار 101 سهم وتوزيع actions |
| `audit/decision_101/live_readiness_build_scaled.log` | سجل التشغيل بعد تصحيح الوحدات |
| `audit/decision_101/run_101_decision_test_final_v2.log` | سجل اختبار الكون النهائي |

## مراجع المصادر

[1]: https://stockanalysis.com/quote/egx/ABUK/financials/ "StockAnalysis EGX financial statements example — explicitly labelled financials in millions EGP"
[2]: https://stockanalysis.com/quote/egx/ABUK/statistics/ "StockAnalysis EGX statistics example — market cap and shares outstanding"
[3]: https://english.mubasher.info/markets/EGX/stocks/ACTF/financial-statements/ "Mubasher EGX financial statements fallback example"
[4]: https://finance.yahoo.com/quote/ABUK.CA/history/ "Yahoo Finance EGX price history example"
