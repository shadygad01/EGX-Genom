# نتيجة Strategic Refactor للقرار

**التاريخ:** 14 أغسطس 2026  
**النطاق:** EGX30/EGX70 — 101 سهمًا

## ما تم تنفيذه

تم توحيد عقد مخرجات القرار بحيث يحتوي كل سهم على `rank` و`opportunity_score` و`market_stance` و`portfolio_action_status` و`expected_return_type` و`confidence_type` و`horizon_label`. أصبحت القيمة الحالية المسماة بالعائد واضحة: `fair_value_upside_plus_macro_momentum` وليست احتمالًا إحصائيًا.

تم فصل موقف السوق عن قرار المحفظة. النظام يعرض `attractive/neutral/unattractive/insufficient_evidence`، بينما `portfolio_action` يبقى فارغًا ويُعلَّم بأنه يحتاج بيانات حيازة المستخدم؛ لذلك لا يدّعي النظام `Increase` أو `Exit` دون معرفة المركز.

تم تغيير ترتيب المخرجات إلى `opportunity_score` موقّع ومعدل بجودة البيانات والتقلب، وليس حاصل `confidence × absolute return`. النتيجة لا تعني أن الصيغة مثبتة تاريخيًا؛ هي عقد ترتيب واضح وقابل للاختبار لاحقًا.

## التحقق الحالي

| الفحص | النتيجة |
|---|---|
| عدد التوصيات | 101/101 |
| الرتب | 1 إلى 101 بلا تكرار |
| تسريب فترة مالية مستقبلية | لم يظهر في التدقيق الحالي |
| Confidence | معلنة كـScore غير معايرة، لا Probability |
| Expected Return | معلن كـFair Value Upside + macro/momentum |
| مصدر تجريبي داخل القرار | لا يوجد |

## المخرجات الحالية

| القرار | العدد |
|---|---:|
| Strong Buy | 1 |
| Buy | 2 |
| Hold | 2 |
| Reduce | 2 |
| Sell | 41 |
| Abstain | 53 |

| الموقف السوقي | العدد |
|---|---:|
| Attractive | 3 |
| Neutral | 2 |
| Unattractive | 43 |
| Insufficient Evidence | 53 |

## ما لم يتم ادعاؤه

لم يتم إنتاج Top-1/3/5/10 تاريخيًا أو Rank IC أو Expected-vs-Realized Return لأن المشروع لا يملك بعد سجلًا نقطيًا كاملًا يربط كل قرار تاريخي بما كان منشورًا وقت القرار وبالعائد اللاحق. كل هذه المقاييس ظاهرة صراحة كـ`null` في `ranking_quality_audit.json` بدل اختلاق نتائج.

كما أن الآفاق الحالية لا تزال `short_term` فقط عندما يكون القرار swing، و`investment_term_unclassified` لبقية الحالات. لم يتم اختلاق تقسيم Medium/Long قبل وجود أهداف وفترات اختبار مناسبة.

## الخطوة الجوهرية المتبقية

قبل تسمية النظام Opportunity Ranking validated، يجب إضافة `published_at` لكل تقرير مالي، وتثبيت `as_of` عند إعادة البناء التاريخي، وتسجيل forward returns في Decision Ledger، ثم تشغيل Walk-forward على Top-1/3/5/10 لكل أفق. هذه ليست مشكلة architecture تستدعي Rewrite؛ إنها فجوة إثبات تاريخي مركزة.
