# Iteration 2026-03-30-ocr-bill-import-and-classification

## Summary
- Improved bill format compatibility analysis for WPS-exported Alipay and WeChat files.
- Investigated why many obvious transactions still fell into `其他`, and expanded built-in category coverage.
- Prepared the taxonomy and rule engine so餐饮、交通、购物、保险、云服务、酒店、转账/储蓄等高频场景 can be recognized earlier without relying on fallback.

## What changed
- Expanded category taxonomy in `backend/app/domain/classification/category_tree.py`
  - Added `餐饮・其他`
  - Added `住房・酒店住宿`
  - Added new L1 category `数码服务`
  - Added `转账・储蓄转移`
- Expanded system rules in `backend/app/domain/classification/rule_engine.py`
  - Added stronger餐饮 coverage for `餐饮 / 美食 / 煎饼 / 便利店 / 罗森 / 赵一鸣` etc.
  - Added交通 coverage for `北京一卡通`
  - Added购物 coverage for `抖音电商 / 小红书 / 闲鱼 / 日用品 / 数码商品`
  - Added医疗健康 coverage for `保险 / 保费 / 好医保`
  - Added住房 coverage for `酒店 / 汉庭 / 全季 / 如家 / 亚朵 / 锦江`
  - Added数码服务 coverage for `阿里云 / 腾讯云 / Vultr / iCloud / DeepSeek / 加速器 / 订阅`
  - Added转账 coverage for `收钱码收款 / 自动转入 / 还款 / 分期 / 贷款`
- Added China Merchants Bank PDF statement support in `backend/app/infrastructure/parsers/cmb.py`
  - Benchmarked direct PDF text extraction, RapidOCR, and EasyOCR on the real uploaded PDF
  - Chose direct embedded-text extraction as the primary path because it preserved more fields than OCR on this statement
  - Kept `rapidocr-onnxruntime` as OCR fallback for scanned PDF cases and removed heavyweight `easyocr`
- Updated parser registration and source display so `cmb` imports appear correctly in backend and frontend
- Added parser regression tests in `backend/tests/test_bill_parsers.py`

## Diagnosis notes
- Existing `其他` transactions are mainly from `fallback`, not from LLM.
- DB inspection showed most misclassifications were caused by missing built-in rules rather than the model randomly classifying into `其他`.
- Example: `北京郭通餐饮管理有限公司朝阳区分公司` was indeed classified by `fallback`, which confirms a system-rule coverage gap.

## Bill compatibility findings
- The problematic Alipay file in `backend/uploads/支付宝交易明细(20250331-20260330).csv` is GB18030/GBK encoded, not UTF-8.
- It contains a long metadata preamble before the actual CSV table header.
- The WPS-opened WeChat `.xlsx` still preserves the expected header row and looks structurally parseable.
- The China Merchants Bank PDF is text-based, not image-only, so OCR is unnecessary for the uploaded sample and performs worse than direct extraction.
- RapidOCR still remains useful as a fallback for future scanned bank statements.

## Validation performed
- Queried production-like Postgres data to inspect current `其他` transactions and their `category_source` distribution.
- Confirmed the majority of `其他` records were `fallback`.
- Previewed the uploaded Alipay CSV with multiple encodings.
- Previewed the uploaded WeChat XLSX rows using the backend runtime environment.
- Benchmarked the uploaded招商银行 PDF with direct PDF text extraction, RapidOCR, and EasyOCR.
- Verified direct extraction and RapidOCR both recovered key statement fields, while EasyOCR lost more Chinese text fidelity on the same sample.
- Added parser regression coverage for the real uploaded PDF/XLSX/CSV files.

## Next
- Re-run import regression and verify the updated rules reduce `其他` substantially.
- Add a targeted backfill/reclassification path for already imported transactions if needed.
- If future bank PDFs are scanned images instead of embedded text, validate whether the RapidOCR fallback is sufficient or whether table-aware OCR is needed.
