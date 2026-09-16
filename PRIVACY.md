# Privacy / Datenschutz

Personal Photo Toolkit is designed as a **local-first desktop application**. The project does not operate a photo-storage service, face-recognition server, analytics backend, advertising network, or user account system.

> This document describes the intended technical behavior of this open-source project. It is not legal advice. If you distribute a modified build or use the software in an organization, you are responsible for assessing the legal requirements that apply to your use.

## What the application processes

Depending on the tool you choose, the application can process photos, videos, file names, file metadata, Google Photos Takeout metadata, cryptographic file hashes, AI classification results, detected faces, face embeddings, reference photos, validation labels, and generated CSV/text reports.

## Local processing

The three tools are designed to process the selected files on the user's own computer. The application does not intentionally upload selected photos, videos, reference photos, face embeddings, classification results, reports, or file hashes to the project maintainers or to a cloud recognition API.

No telemetry, advertising SDK, or analytics collection is enabled by this project by default.

## Internet access and model downloads

The basic **Organize by Year** tool does not need an AI model download.

The **Trip Photo Filter** needs a face-analysis model. Before the first model download, the UI asks the user for confirmation and explains the approximate download size. The model file is downloaded from the model provider and cached locally. The user's selected photos are not intentionally included in that model-download request.

The **Photo Cleaner** similarly requires a CLIP model. The UI asks before the first model download. After download, image classification is performed locally by this application.

Third-party download hosts may receive ordinary network information such as the user's IP address when a model is downloaded. Their own privacy policies apply to those network requests.

## Face recognition and biometric data

Trip Photo Filter uses reference photographs to create mathematical face embeddings and compares faces in trip photographs against those embeddings. Face recognition can involve biometric personal data, especially when facial data is processed for the purpose of uniquely identifying a person.

Users should only process images when they have a lawful basis or other permission required for their situation. Extra care is appropriate for shared collections, workplace use, public deployment, children, or other sensitive contexts.

Reference photos and generated embeddings are not intentionally sent to the project maintainers. The application does not use them to retrain the underlying recognition model.

## Accuracy and human review

Face recognition and AI image classification are probabilistic. They can make false matches and miss real matches. The application therefore uses `Review` categories and does not automatically delete original media.

An accuracy percentage is only produced when the user supplies labeled positive and negative validation photos. That result describes the supplied validation set and is not a guarantee for future photos.

## Originals and deletion

The toolkit is designed to copy organized results into a destination folder. It does not intentionally delete source photos automatically. Users remain responsible for reviewing output before deleting or moving originals.

Users can remove local outputs, reports, reference photos, model caches, and application settings from their own computer whenever they choose.

## Third-party software and model licensing

Open-source software dependencies and pretrained AI models have their own licenses. In particular, InsightFace code and its pretrained model packs do not have identical licensing terms. Review the upstream model license before redistribution or commercial use.

## Changes by forks and redistributors

This privacy description applies to the source code in this repository. A fork or third-party binary can change the behavior. Users should obtain releases from a source they trust; maintainers of modified distributions should update this document to accurately describe their build.

---

# Kurzfassung auf Deutsch

**Personal Photo Toolkit ist als lokal arbeitende Desktop-Anwendung konzipiert.** Ausgewählte Fotos, Videos, Referenzfotos, Gesichts-Embeddings und erzeugte Berichte werden von diesem Projekt nicht absichtlich an die Projektbetreiber oder an einen Cloud-Dienst zur Gesichtserkennung übertragen. Standardmäßig enthält das Projekt keine Telemetrie und keine Werbung.

Für den Trip Photo Filter und den Photo Cleaner müssen optionale KI-Modelle heruntergeladen werden. Vor dem ersten größeren Modelldownload zeigt die Anwendung einen Hinweis und fragt nach Bestätigung. Beim Download können beim jeweiligen Drittanbieter übliche Verbindungsdaten wie die IP-Adresse anfallen; dessen Datenschutzbestimmungen gelten für diesen Download.

Der Trip Photo Filter verarbeitet Gesichtsmerkmale, um zu prüfen, ob eine ausgewählte Referenzperson auf einem Foto vorkommt. Je nach Zweck und Nutzungskontext kann dies die Verarbeitung biometrischer personenbezogener Daten darstellen. Nutzer:innen müssen selbst prüfen, ob für ihre konkrete Nutzung eine geeignete Rechtsgrundlage bzw. erforderliche Einwilligung vorliegt. Dies gilt besonders bei organisatorischer/geschäftlicher Nutzung, bei Fotos Dritter und bei sensiblen Personengruppen.

Die KI-Ergebnisse sind nicht fehlerfrei. Deshalb gibt es `Review`-Ordner, und Originaldateien werden nicht automatisch gelöscht. Eine angezeigte Genauigkeit bezieht sich nur auf die von der Nutzerin/dem Nutzer bereitgestellten, gelabelten Validierungsfotos und ist keine Garantie für zukünftige Bilder.

Diese Datenschutzhinweise beschreiben das beabsichtigte Verhalten des Quellcodes dieses Repositories und stellen keine Rechtsberatung dar. Forks oder fremde Binärdateien können ein anderes Verhalten haben.
