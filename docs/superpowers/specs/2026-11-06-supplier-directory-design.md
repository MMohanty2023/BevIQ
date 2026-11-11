# Supplier Directory Design

## Intent

Dashboard me Master Brand data ka supplier-wise view dena. User ko total distinct suppliers dikhne chahiye, aur har supplier ke liye alag expandable div/card me related summary aur brand information milni chahiye.

## Goals

- Distinct supplier ka total count dikhana.
- Har supplier ko separate card/div me show karna.
- Card me supplier ka record/product count, distinct brand count, brand names, aur UPC count dikhana.
- Card ko expand/collapse karna aur supplier name se filter/search karna.
- Data live active database ke Master Brand table se lena.

## Non-goals

- Supplier ya brand data ko edit/delete karna.
- Existing Master Brand search flow ko replace karna.
- Categorization tables ke supplier fields ko Master Brand supplier summary me mix karna.

## Approach

Chosen approach: searchable expandable supplier cards. Har card initially compact summary dikhayega; expand karne par brand names aur related Master Brand product rows dikhengi. Isse supplier-wise visual grouping bani rahegi aur large dataset me page usable rahega.

Alternative considered: single supplier table. Ye compact hoti, lekin user ke supplier-wise separate div requirement se match nahi karti. Alternative: har supplier ka always-expanded full detail card. Ye large supplier list me page ko unnecessarily lamba aur slow bana sakta hai.

## Data/API

- New read-only endpoint `/api/dashboard/suppliers`.
- Response me `total_suppliers` aur supplier objects honge.
- Har supplier object me supplier name, record count, brand count, sorted brand names, UPC count, aur limited product/brand detail rows honge.
- Blank/null supplier values ko `NA` category/bucket me group kiya jayega.

## UI behavior

- Dashboard me existing metrics ke neeche dedicated Supplier Directory div.
- Header me total supplier count aur search input.
- Supplier cards alphabetical order me.
- Search karne par matching supplier cards visible rahenge.
- Expand/collapse control accessible button ke roop me hoga.
- Empty/error state clearly show hoga.

## Verification

- API test distinct supplier aggregation, brand counts, brand names, and blank supplier handling verify karega.
- Frontend contract test endpoint aur required UI hooks verify karega.
- Existing test suite run ki jayegi.
