# IPP offline – Home Assistant

Copie de l'intégration officielle **Internet Printing Protocol (IPP)** de Home Assistant, modifiée pour les
imprimantes **souvent éteintes** : une imprimante fermée est un état normal « hors ligne », pas une erreur.

**Version de référence : HA core `2026.10.2`** (`homeassistant/components/ipp`). Le premier commit de ce dépôt est
le code officiel non modifié ; `git diff <premier commit>` montre exactement les changements.

## Différences avec l'intégration officielle

- Imprimante éteinte : plus de « Échec de la configuration, nouvel essai » au démarrage de HA. Les vraies erreurs
  IPP (réponse invalide, version non supportée…) restent des erreurs.
- Le capteur d'état de l'imprimante affiche `offline` ; encres, compteurs et uptime deviennent indisponibles.
- Nouveau capteur binaire **En ligne** (connectivité, diagnostic) pour les automatisations.
- Si HA démarre imprimante éteinte, les capteurs d'encre/compteurs sont créés au premier allumage.
- Logs : une seule ligne `info` au passage en ligne / hors ligne.

## Installation

**HACS** : *Dépôts personnalisés* → `https://github.com/djiesr/ipp-offline`, catégorie *Intégration*, installer
puis redémarrer HA.

**Manuelle** : copier `custom_components/ipp` dans le dossier `custom_components` de HA, puis redémarrer.

Même domaine (`ipp`) : la configuration et les entités existantes sont reprises. HA affichera l'avertissement normal
« custom integration ipp overrides core ».

## Mise à jour quand HA change l'intégration officielle

Comparer `homeassistant/components/ipp` de la nouvelle version de HA avec le premier commit, reporter les
changements, puis réappliquer le diff de ce dépôt. Pour revenir à l'officielle : supprimer
`custom_components/ipp` (ou la désinstaller dans HACS) et redémarrer.

## Licence

Code dérivé de [Home Assistant](https://github.com/home-assistant/core), sous licence Apache 2.0 (voir
[LICENSE.md](LICENSE.md)). Les modifications par rapport à l'original sont visibles dans l'historique git.
