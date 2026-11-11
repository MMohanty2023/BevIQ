# Trained Dataset Design

## Intent

Add a Trained Dataset dashboard to the existing BevIQ application using the real `TrainedBrandsData.csv` sheet, while preserving the existing Dashboard, Master Brands, Comparison Studio, Datasets, and AI Assistant experiences.

## Data and boundaries

The trained sheet contains 15,839 rows and fields for IDs, supplier/brand identifiers, category, image counts/URLs, status, SKU, model, and average trained photos. It will be ingested into a dedicated `trained_brands` table using the existing loader conventions and indexed for search. No source rows are modified or duplicated in the source files.

## Approach

Add server-side endpoints for summary/analytics, paginated records, record detail, and export. Add a single navigation tab and dashboard panel using the existing vanilla-JS design system; charts are rendered with native SVG/CSS and update from the same filtered analytics payload. Extend the existing `RAGOrchestrator` with trained-dataset intent routing and SQL retrieval; the existing chat endpoint, history, model configuration, and UI remain unchanged.

## Source mapping

`Id` is the record ID, `Class Id` the class ID, `SupplierCode`/`SupplierName` the supplier fields, `BrandCode`/`BrandName` the brand fields, `Category (Wine/Spirits/Beer/Non Alcoholic)` the category, `ImageCounts` and `AvgTrainedPhotos` the training metrics, `SKU` the SKU, `Status`/`RecordStatus` the status fields, `Model`/`Model Id` the model fields, and `ImageUrls` the product/brand image gallery. Category art is UI-only and separate from source images.

## Non-goals

No replacement chatbot, no changes to existing Master Brand search behavior, no fabricated source values, and no changes to unrelated pages or database records.
