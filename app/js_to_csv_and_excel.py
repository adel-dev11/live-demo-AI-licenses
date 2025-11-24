# # # import pandas as pd
# # # import json

# # # # 1. تحميل الـ JSON
# # # with open(r'C:\Users\adel mohamedll\Desktop\Hackathon\licenses.json', encoding='utf-8') as f:
# # #     data = json.load(f)

# # # df = pd.json_normalize(data['licenses'])

# # # # 3. عمل الليبل (غيّر الشرط حسب تعريفك للأمان)
# # # permissive = {'MIT', 'BSD-3-Clause', 'BSD-2-Clause', '0BSD', 'Apache-2.0', 
# # #               'ISC', 'Zlib', 'Unlicense', 'CC0-1.0', 'WTFPL'}
# # # df['is_safe'] = df['licenseId'].isin(permissive).astype(int)   # 1 = آمن، 0 = مش آمن

# # # # 4. تنظيف الأعمدة اللي مش محتاجها
# # # df = df.drop(columns=['reference', 'detailsUrl', 'referenceNumber', 
# # #                       'seeAlso', 'isDeprecatedLicenseId'], errors='ignore')

# # # print(df[['licenseId', 'name', 'isOsiApproved', 'is_safe']].head(10))
# # # print(f"إجمالي التراخيص: {len(df)}")
# # # print(f"تراخيص آمنة (permissive): {df['is_safe'].sum()}")



# # import pandas as pd
# # import json

# # # 1. تحميل الداتا
# # with open(r'C:\Users\adel mohamedll\Desktop\Hackathon\licenses.json', encoding='utf-8') as f:
# #     data = json.load(f)

# # df = pd.json_normalize(data['licenses'])

# # # 2. قوائم التراخيص حسب المخاطر (ممكن تزود أو تغير براحتك)
# # SAFE_LICENSES = {
# #     'MIT', 'Apache-2.0', 'BSD-3-Clause', 'BSD-2-Clause', 'BSD-1-Clause', '0BSD',
# #     'ISC', 'Zlib', 'Unlicense', 'CC0-1.0', 'WTFPL', 'Python-2.0', 'PostgreSQL',
# #     'Artistic-2.0', 'OFL-1.1', 'UPL-1.0'
# # }

# # MODERATE_LICENSES = {
# #     'LGPL-2.0-only', 'LGPL-2.0-or-later', 'LGPL-2.1-only', 'LGPL-2.1-or-later',
# #     'LGPL-3.0-only', 'LGPL-3.0-or-later', 'MPL-1.1', 'MPL-2.0', 'EPL-1.0', 'EPL-2.0',
# #     'CDDL-1.0', 'CDDL-1.1', 'CPL-1.0'
# # }

# # STRONG_COPYLEFT = {
# #     'GPL-1.0-only', 'GPL-1.0-or-later', 'GPL-2.0-only', 'GPL-2.0-or-later',
# #     'GPL-3.0-only', 'GPL-3.0-or-later', 'AGPL-1.0-only', 'AGPL-3.0-only',
# #     'AGPL-3.0-or-later'
# # }

# # # 3. إنشاء عمود risk_level
# # def get_risk_level(row):
# #     lid = row['licenseId']
# #     deprecated = row['isDeprecatedLicenseId']
    
# #     if deprecated:
# #         return 'DANGEROUS'          # أي ترخيص قديم = خطير
# #     elif lid in SAFE_LICENSES:
# #         return 'SAFE'
# #     elif lid in MODERATE_LICENSES:
# #         return 'MODERATE'
# #     elif lid in STRONG_COPYLEFT:
# #         return 'RESTRICTED'
# #     else:
# #         # أي ترخيص مش في القوائم = غير معروف = خطير
# #         return 'DANGEROUS'

# # df['risk_level'] = df.apply(get_risk_level, axis=1)

# # # 4. عمود إضافي بسيط: is_safe (binary) لو عايز تدرب مودل بعدين
# # df['is_safe'] = df['risk_level'].apply(lambda x: 1 if x == 'SAFE' else 0)

# # # 5. ترتيب الأعمدة عشان تبقى مرتبة وجميلة
# # final_columns = [
# #     'licenseId', 'name', 'isOsiApproved', 'isDeprecatedLicenseId',
# #     'risk_level', 'is_safe'
# # ]
# # df_final = df[final_columns].sort_values(['risk_level', 'licenseId'])

# # # 6. حفظ الملفات الجديدة
# # df_final.to_csv('licenses_with_risk_classification.csv', index=False, encoding='utf-8-sig')
# # df_final.to_excel('licenses_with_risk_classification.xlsx', index=False)

# # print("تم الحفظ بنجاح!")
# # print(df_final['risk_level'].value_counts())
# # print("\nأول 15 ترخيص:")
# # print(df_final.head(15)[['licenseId', 'name', 'risk_level']])

import pandas as pd
import json

with open(r'C:\Users\adel mohamedll\Desktop\Hackathon\licenses.json', encoding='utf-8') as f:
    data = json.load(f)


df = pd.json_normalize(data['licenses'])

print(f"عدد التراخيص في الملف الأصلي: {len(df)}")  


def smart_risk_classification(row):
    lid = row['licenseId']
    name = row['name'].lower()
    deprecated = row['isDeprecatedLicenseId']
    osi = row['isOsiApproved']

    
    if deprecated:
        return 'DANGEROUS'

   
    if osi and any(x in lid.upper() for x in ['MIT','BSD','APACHE','ISC','0BSD','ZLIB','UNLICENSE','CC0','WTFPL','BSL','UPL']):
        return 'SAFE'

    if 'permissive' in name or 'bsd' in name or 'mit' in name or 'apache' in name or 'isc' in name:
        return 'SAFE'

    if any(x in lid.upper() for x in ['LGPL','MPL','EPL','CDDL','CPL']):
        return 'MODERATE'

    if any(x in lid.upper() for x in ['GPL','AGPL']):
        return 'RESTRICTED'

    if osi:
        return 'MODERATE'   

   
    return 'DANGEROUS'


df['risk_level'] = df.apply(smart_risk_classification, axis=1)
df['is_safe'] = (df['risk_level'] == 'SAFE').astype(int)


final_columns = [
    'licenseId',
    'name',
    'isOsiApproved',
    'isDeprecatedLicenseId',
    'risk_level',
    'is_safe'
]

df_output = df[final_columns].sort_values(['risk_level', 'licenseId']).reset_index(drop=True)


df_output.to_csv('all_licenses.csv', index=False, encoding='utf-8-sig')
df_output.to_excel('all_licenses.xlsx', index=False)

# 7. تأكيد نهائي
print("تم بنجاح! كل التراخيص موجودة في الملف الجديد")
print(f"إجمالي عدد التراخيص في الملف الجديد: {len(df_output)}")
print("\nالتوزيع:")
print(df_output['risk_level'].value_counts())

# import pandas as pd
# import json

# # تحميل الـ JSON
# with open(r'C:\Users\adel mohamedll\Desktop\Hackathon\licenses.json', encoding='utf-8') as f:
#     data = json.load(f)

# df = pd.json_normalize(data['licenses'])

# print(f"عدد التراخيص في الملف: {len(df)}")

# # دالة التصنيف + الشرح بالعربي
# def classify_and_explain(row):
#     lid = row['licenseId']
#     name = row['name'].lower()
#     deprecated = row['isDeprecatedLicenseId']
#     osi = row['isOsiApproved']

#     if deprecated:
#         return 'DANGEROUS', 'ترخيص قديم ومُلغى رسميًا من SPDX – ممنوع استخدامه'

#     # SAFE – Permissive
#     if any(x in lid.upper() for x in ['MIT','BSD','APACHE','ISC','0BSD','ZLIB','UNLICENSE','CC0','WTFPL','BSL','UPL','POSTGRESQL','OFL']):
#         return 'SAFE', 'ترخيص مفتوح تمامًا (Permissive) – آمن 100% في المشاريع التجارية والمغلقة'

#     if 'permissive' in name or 'bsd' in name or 'mit' in name or 'apache' in name or 'isc' in name:
#         return 'SAFE', 'ترخيص مفتوح تمامًا (Permissive) – آمن 100% في المشاريع التجارية والمغلقة'

#     # MODERATE – Weak Copyleft
#     if any(x in lid.upper() for x in ['LGPL','MPL','EPL','CDDL','CPL']):
#         return 'MODERATE', 'ترخيص ضعيف النسخ (Weak Copyleft) – مسموح بس يحتاج مراجعة ديناميكية/ستاتيك لينك'

#     # RESTRICTED – Strong Copyleft
#     if any(x in lid.upper() for x in ['GPL','AGPL']):
#         return 'RESTRICTED', 'ترخيص نسخ قوي (Strong Copyleft) – يُلزمك بفتح كود مشروعك كاملاً لو وزّعته'

#     # باقي الـ OSI Approved نعتبره معتدل
#     if osi:
#         return 'MODERATE', 'ترخيص معتمد من OSI لكن غير شائع – يحتاج مراجعة قانونية قبل الاستخدام'

#     # كل الباقي خطير
#     return 'DANGEROUS', 'ترخيص غير معروف أو مخصص أو غير موثوق – ممنوع استخدامه بدون موافقة Legal'

# # تطبيق الدالة
# df[['risk_level', 'risk_explanation_ar']] = df.apply(
#     lambda row: pd.Series(classify_and_explain(row)), axis=1
# )

# # عمود is_safe بسيط
# df['is_safe'] = (df['risk_level'] == 'SAFE').astype(int)

# # ترتيب الأعمدة النهائي في الملف
# final_columns = [
#     'licenseId',
#     'name',
#     'isOsiApproved',
#     'isDeprecatedLicenseId',
#     'risk_level',
#     'is_safe',
#     'risk_explanation_ar'
# ]

# df_final = df[final_columns].sort_values(['risk_level', 'licenseId']).reset_index(drop=True)

# # حفظ الملفات (كل التراخيص موجودة + الشرح بالعربي)
# df_final.to_csv('كل_التراخيص_مع_شرح_عربي.csv', index=False, encoding='utf-8-sig')
# df_final.to_excel('كل_التراخيص_مع_شرح_عربي.xlsx', index=False)

# # إحصائيات سريعة
# print("\nتم بنجاح 100%")
# print(f"إجمالي التراخيص في الملف الجديد: {len(df_final)}")
# print("\nالتوزيع:")
# print(df_final['risk_level'].value_counts())

# print("\nأمثلة من الملف الجديد:")
# print(df_final[['licenseId', 'name', 'risk_level', 'risk_explanation_ar']].head(10))