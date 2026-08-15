# EGX-Genom — وثيقة تسليم الحالة الحالية

**تاريخ التوثيق:** 15 أغسطس 2026، بتوقيت القاهرة  
**المشروع:** `shadygad01/EGX-Genom`  
**الفرع المستهدف:** `main`  
**آخر commit موثق قبل هذا التغيير:** `5af37af` — `feat: enable verified shadow fund allocation views`

## 1. الهدف الحالي والمرحلة

المشروع انتقل من منصة بحث إلى نظام تشغيل لصندوق استثماري يغطي نطاق EGX30 وEGX70 كاملًا. المرحلة الحالية هي **تشغيل Fund Manager cockpit مع تدفقات تخصيص رأس المال، مع الحفاظ على نزاهة البيانات ومنع أي قرار شخصي أو تنفيذ حي دون خدمة تشغيلية وبيانات حديثة**.

الخطوة الأخيرة كانت معالجة الخصائص التي كانت تظهر للمستخدم كـ `Needs a live backend` في لوحة CIO Desk. تم تفعيل ما يمكن تفعيله بأمان من artifacts الإنتاج العامة، مع إبقاء القرارات المرتبطة بحيازات المستثمر الشخصية محجوبة عمدًا لأنها تحتاج backend تشغيليًا.

> القاعدة الحاكمة: لا يتم اختلاق بيانات، ولا تحويل خطة shadow fund إلى قرار شخصي، ولا إزالة freshness gate لمجرد إظهار حالة أكثر نشاطًا.

## 2. الحالة الإنتاجية الحالية

| البند | الحالة الموثقة |
|---|---|
| الفرع | `main` |
| آخر commit قبل وثيقة التسليم | `5af37af` |
| النشر | GitHub Pages حي |
| نمط البيانات الحي | `pipeline_mode=live` |
| آخر snapshot سوق حقيقي | 13 أغسطس 2026 |
| تاريخ التوليد | 14 أغسطس 2026 |
| تغطية الأسهم السعرية | 101/101 |
| ترتيب الأسهم | فريد من 1 إلى 101 |
| التغطية القطاعية | 13 مصنفًا، و88 `Unclassified` بشكل صريح بسبب فجوة المصدر |
| حالة التنفيذ الحي | محجوبة عند قدم snapshot، ولا يجوز تجاوزها |
| shadow fund artifact | موجود، تاريخه 13 أغسطس 2026، ويحتوي خطة تخصيص موثقة |
| Web lint/typecheck | ناجح |
| Web tests | 68/68 ناجحة |
| Web production build | ناجح |
| آخر Deploy معروف | ناجح للـ commit `5af37af` |

## 3. ما تم إنجازه بالكامل

### 3.1 التغطية والنزاهة المالية

تم الوصول إلى تغطية سعرية كاملة لـ101 سهم مع ترتيب فريد من 1 إلى 101. تم بناء مسارات تغطية القوائم المالية عبر مصادر متعددة، مع تطبيق مبدأ عدم تصنيع القيم. الأسهم التي لا يتوفر لها قطاع موثق تظهر صراحة كـ `Unclassified` بدل تخمين قطاع.

تم تطبيق بوابات قرار تمنع التوصية الاستثمارية عندما لا يتوفر سعر صالح أو قيمة عادلة مبنية على أدلة كافية ومتسقة. حالات `Abstain` ليست أخطاء واجهة؛ هي نتيجة مقصودة عندما لا تتوافر الأدلة المطلوبة.

### 3.2 Fund Manager Action Queue

تمت إضافة طابور إجراءات مدير الصندوق إلى CIO Desk، مع فصل:

- فرص قابلة للتنفيذ، subject to freshness gate.
- فرص محجوبة مع سبب `Why Not` الفعلي.
- مراجعة، سعر مرجعي، confidence، expected return، entry condition، وتاريخ المراجعة.

في snapshot الحالي لا توجد فرصة تتجاوز بوابة التنفيذ الحي، وهو سلوك صحيح لأن آخر snapshot يعود إلى 13 أغسطس واليوم 15 أغسطس.

### 3.3 Data Freshness & Execution Eligibility

تم تطبيق بوابة fail-closed تمنع التنفيذ الحي إذا تجاوز عمر snapshot الحد المسموح. لا يجوز تشغيل `force_live` في يوم غير تداولي أو إعادة تسمية snapshot قديم إلى تاريخ اليوم. جلسة 15 أغسطس 2026 يوم سبت، ولذلك ظل الحظر سليمًا.

### 3.4 إصلاح deploy وcanonical manifest

تم إصلاح workflow بحيث لا تؤدي دفعات الكود فقط إلى فقدان artifacts الحية أو الرجوع إلى replay mode. النشر يحتفظ بالـ canonical live manifest عندما لا توجد جلسة جديدة.

الـ manifest الحي الحالي يثبت:

```json
{
  "pipeline_mode": "live",
  "source_data_as_of": "2026-08-13",
  "generated_at": "2026-08-14T20:14:21.345014"
}
```

### 3.5 إصلاح الرسالة التقنية للمستخدم

كانت صفحة Portfolio تعرض `error.message` الخام، بما في ذلك تعليمات تشغيل محلية مثل `npm run dev` و`DECISION_DATA_DIR`. تم استبدال ذلك بحالة مستخدم واضحة ومترجمة:

> القرارات الشخصية غير متاحة في النسخة المنشورة.

وتشرح أن بيانات السوق والأبحاث والقرارات العامة متاحة، بينما القرارات المرتبطة بحيازات المستثمر تحتاج خدمة قرار تشغيلية آمنة.

التغيير محفوظ في commit `78773e6`.

### 3.6 تفعيل أقسام تخصيص رأس المال من shadow fund

تم ربط CIO Desk بـ `shadow_fund.capital_allocation_plan` عندما لا توجد خطة شخصية من `ApiProvider`. هذا artifact حقيقي وموثق، ويُعرض كمرجع نموذجي فقط.

الأقسام التي أصبحت تعمل من الخطة الموثقة:

| القسم | السلوك الحالي |
|---|---|
| Capital Deployment Queue | يعرض queue الموثق أو empty state الصادق |
| Capital Recycling | يعرض التدفقات إن وجدت أو يوضح عدم الحاجة للتدوير |
| Capital Released Today | يعرض التخفيضات الموثقة إن وجدت |
| Best New Opportunities | يعرض الفرص الجديدة أو empty state |
| Highest Opportunity Cost | يعرض EXPA وARCC في snapshot الحالي |
| Allocation Changes | يعرض الفروق الموثقة أو يوضح عدم وجود تغييرات |
| Capital Waiting | يعرض idle cash before/after وسبب الانتظار |

تمت إضافة ترجمتين تميزان بوضوح بين:

- `sourceLive`: خطة مخصصة لحيازات المستخدم عبر backend.
- `sourceShadowFund`: خطة shadow fund موثقة، نموذجية وغير مخصصة.

التغيير محفوظ في commit `5af37af`.

## 4. ما يزال محجوبًا ولماذا

الخاصية الوحيدة الجوهرية التي لم تُفعّل في GitHub Pages هي **القرارات الشخصية المرتبطة بحيازات المستخدم**، وتشمل Buy / Increase / Hold / Reduce / Exit الموزونة على محفظة فعلية.

السبب ليس نقصًا في واجهة React، بل طبيعة التشغيل:

1. القرار يحتاج current holdings وcurrent weight وaverage cost والسيولة.
2. القرار يحتاج تشغيل `decision_service` عند الطلب، وليس artifact عامًا.
3. تخصيص رأس المال يحتاج معرفة مصدر تمويل كل تغيير ومراكز المستخدم.
4. بيانات الحيازة لا يجوز نشرها داخل GitHub Pages أو artifacts عامة.
5. قرار شخصي قديم لا يجوز إعادة استخدامه بعد تغير snapshot أو freshness.

المشروع يحتوي بالفعل على `ApiProvider` وFastify API ومسارات:

- `POST /api/decisions`
- `POST /api/capital-allocation`

لكن GitHub Pages يستخدم `VITE_DATA_PROVIDER=static` لأنه لا يشغل backend. يوجد إعداد تطوير محلي وإعداد self-hosted، لكن لا توجد حاليًا خدمة API عامة مستضافة ومؤمنة مربوطة بالموقع الحي.

## 5. البنية التقنية المهمة

| المسار | الوظيفة |
|---|---|
| `web/src/pages/CIODesk.tsx` | لوحة مدير الصندوق، Action Queue، Capital Allocation، shadow fallback |
| `web/src/pages/Portfolio.tsx` | إدخال الحيازات وعرض القرارات الشخصية عند توفر API |
| `web/src/data/StaticJsonProvider.ts` | قراءة artifacts ورفض POST الشخصي في static mode |
| `web/src/data/ApiProvider.ts` | اتصال API الحي ومسارات القرارات والتخصيص |
| `web/src/data/factory.ts` | اختيار provider حسب `VITE_DATA_PROVIDER` |
| `web/.env.production` | مضبوط حاليًا على `VITE_DATA_PROVIDER=static` |
| `api/src/routes/decisions.ts` | تشغيل CLI decision service عند الطلب |
| `web/src/hooks/usePortfolioPositions.ts` | تخزين حيازات المستخدم محليًا في المتصفح فقط |
| `web/public/data/manifest.json` | canonical publication manifest |
| `web/public/data/market_state.json` | snapshot السوق والتغطية والأسعار |
| `web/public/data/shadow_fund.json` | حالة shadow fund وخطة التخصيص الموثقة |
| `.github/workflows/deploy-pages.yml` | build، حفظ canonical state، validation، نشر GitHub Pages |
| `audit/validate_live_dashboard.py` | التحقق المستقل من artifacts والتغطية |
| `docs/decision-system/research_module_manifest.json` | حوكمة وحدات البحث والاختبارات الإلزامية |

## 6. الاختبارات التي تم اجتيازها

آخر تشغيل محلي للواجهة اجتاز:

```text
TypeScript lint: PASS
Web test files: 7 passed
Web tests: 68 passed
Production build: PASS
```

الاختبارات تشمل `ApiProvider`, `StaticJsonProvider`, `App`, `factory`, `format`, `provenance`, و`truthPreservation`.

تم كذلك التحقق بصريًا من CIO Desk بعد نشر `5af37af`، وظهرت خطة shadow fund والفرص ذات تكلفة الفرصة البديلة بدل بطاقات `يتطلب خادمًا حيًا`.

## 7. ما يجب على agent التالي فعله

### أولوية 1 — جلسة EGX التالية

عند أول جلسة تداول مصرية فعلية تالية:

1. تحقق من التاريخ وساعات التداول.
2. شغّل workflow مع `force_live=true` فقط عند توفر جلسة فعلية.
3. تحقق من أن `source_data_as_of` يساوي آخر جلسة حقيقية.
4. شغّل `audit/validate_live_dashboard.py`.
5. شغّل `audit/test_production_contract.py` والاختبارات الكاملة.
6. تأكد من أن execution gate انتقل من blocked إلى eligible فقط إذا صار snapshot ضمن حد freshness.

### أولوية 2 — تفعيل backend الشخصي

لا تبدأ بتغيير `StaticJsonProvider` إلى نتائج مصطنعة. المسار الصحيح:

1. اختيار خدمة استضافة API دائمة وآمنة.
2. نشر `api/` مع `DECISION_DATA_DIR` و`researchDir` و`universeSeedDir` صحيحة.
3. إضافة CORS وHTTPS ومصادقة مناسبة.
4. تخزين حيازات المستخدم في المتصفح أو مخزن خاص، وعدم إدخالها في static artifacts.
5. ضبط `VITE_DATA_PROVIDER=api` في build منفصل أو إعداد runtime قابل للتبديل.
6. اختبار `POST /api/decisions` و`POST /api/capital-allocation` مع بيانات مستخدم اختبارية غير إنتاجية.
7. التأكد أن API يعيد قرارات position-aware فقط بعد freshness والـ provenance gates.

### أولوية 3 — زيادة التاريخ التقييمي

لوحة الاستثمار تشير إلى أن system maturity ما زالت مبكرة لأن عدد نتائج benchmark-evaluated قليل. لا ترفع maturity يدويًا؛ يجب تشغيل جلسات متتابعة وحفظ decision history وshadow fund history ثم إعادة تقييم الأداء.

## 8. ممنوعات الاستكمال

يجب على أي agent لاحق عدم القيام بالآتي:

- عدم اختلاق قطاعات أو قوائم مالية أو أسعار تنفيذ.
- عدم تسمية خطة shadow fund كخطة شخصية للمستخدم.
- عدم إزالة freshness gate لتجميل الواجهة.
- عدم نشر حيازات المستخدم داخل GitHub Pages أو production artifacts العامة.
- عدم تشغيل force_live في عطلة أو بدون مصدر حقيقي.
- عدم حذف `Unclassified` إلا بعد توفر مصدر موثق.
- عدم ضم الملفات البحثية غير المتتبعة عشوائيًا إلى main.

## 9. روابط التشغيل

- [الموقع الحي](https://shadygad01.github.io/EGX-Genom/)
- [CIO Desk](https://shadygad01.github.io/EGX-Genom/)
- [Portfolio](https://shadygad01.github.io/EGX-Genom/portfolio)
- [Market](https://shadygad01.github.io/EGX-Genom/market)
- [Research](https://shadygad01.github.io/EGX-Genom/research)
- [Monitoring](https://shadygad01.github.io/EGX-Genom/monitoring)

## 10. خلاصة تنفيذية

النظام في وضع **canonical production-ready للنسخة static العامة**: تغطية 101/101، ترتيب فريد، artifacts حية، freshness gate، Action Queue، shadow-fund allocation views، وCI/build/deploy عاملون.

النظام ليس بعد **personalized live fund manager service** لأن ذلك يتطلب API مستضافة وآمنة. هذا القيد موثق ومتعمد، وليس فشلًا مخفيًا. المرحلة التالية الصحيحة هي إما استضافة API الشخصية، أو انتظار جلسة تداول جديدة لتحديث snapshot، مع إبقاء كل بوابات النزاهة فعالة.

**آخر تحديث للوثيقة:** 15 أغسطس 2026.
