# Kaggle collection guide

Login karke **Datasets** kholen aur yeh search phrases paste karein. Yeh keywords hain, guaranteed suitable datasets nahi.

| Module | Search phrases | Required evidence |
| --- | --- | --- |
| Anemia, eye | `conjunctival pallor anemia hemoglobin`, `Eyes Defy Anemia`, `CP-AnemiC` | Conjunctiva photos, lab Hb with units, age/sex, patient IDs |
| Anemia, nail | `fingernail anemia hemoglobin`, `anemia fingernails Ghana` | Original nail photos linked to Hb; augmentation lineage |
| Skin | `clinical skin images eczema tinea acne`, `SCIN`, `SkinDisNet`, `Fitzpatrick17k` | Clinician labels, patient/site IDs, healthy/other examples, diverse skin tones |
| Posture | `posture assessment landmarks physiotherapy`, `standing posture assessment` | Front/side standing photos, expert angles/landmarks, patient IDs |
| Scoliosis | `scoliosis surface topography clinical`, `scoliosis standing photograph clinical labels` | Clinician-linked ground truth; yoga poses or X-ray-only data do not train our phone task |
| Eye | `external eye cataract clinical images`, `red eye conjunctivitis clinical images`, `sclera jaundice bilirubin` | External-eye photos, confirmed diagnosis/bilirubin, normal eyes, patient IDs |
| Wound | `wound segmentation masks`, `CO2Wounds`, `diabetic foot ulcer segmentation` | Paired masks, patient IDs; scale reference for centimeters, linked visits for healing |
| Tongue | `tongue segmentation masks`, `tongue coating clinical images`, `tongue lesion diagnosis` | ROI masks for detection; verified clinical labels for disease, patient IDs |

## Download steps

1. Data Card, Data tab aur original paper/repository dekhein. Version aur original image/patient count note karein.
2. Original license check karein. Mirror MIT/Apache declaration original noncommercial terms override nahi karti.
3. Sample photos check karein: real originals hain? Task sahi hai? Metadata CSV/XLSX aur masks available hain?
4. ZIP ke saath metadata, annotations aur license download karein.
5. ZIP ko `D:\Medical Mobile APP\ai-server\datasets\incoming\<dataset-name>\source.zip` mein rakhein.
6. `source-notes.txt` mein Kaggle URL, original URL, version, license, original image/patient count aur intended module likhein. Password/API keys is file mein na rakhein. Unknown dataset scripts execute na karein.

Already acquired mirrors — dobara download ki zaroorat nahi:

- https://www.kaggle.com/datasets/karankumar4090/cp-anemic-dataset-same
- https://www.kaggle.com/datasets/kritagyadev/anemia-using-fingernails-image-datasets-from-ghana
- https://www.kaggle.com/datasets/orvile/leprosy-chronic-wound-images-co2wounds-v2
- https://www.kaggle.com/datasets/samurarahman14/skindisnet-3

Zyada independent, correctly labeled, diverse patients help kar sakte hain; resized duplicates/augmentation independent evidence nahi. Same patient/visit/augmentation family partitions cross na kare. Augmentation training split banne ke baad karein. Different Kaggle collections often same original data mirror karti hain; cross-source deduplication zaroori hai. HAM10000 dermoscopy, fundus eye photos aur yoga poses proposed phone-camera tasks ka substitute nahi.

Image count ya notebook ka 99% score product accuracy establish nahi karta. Patient/site-separated tests, calibration, unknown-condition rejection aur independent Pakistan evaluation abhi bhi required hain.
