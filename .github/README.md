# Arctic Fuse Home TV

Variante di [Arctic Fuse 3 di jurialmunkey](https://github.com/jurialmunkey/skin.arctic.fuse.3)
con canali TV in verticale nella Home, programma e orari sulla destra, e menu
originale della skin per Film, Serie TV e le altre sezioni.

**Base attuale:** Arctic Fuse 3.3.12. **Home TV:** 1.0.3.
Il pacchetto iniziale corrisponde esattamente a quello provato sulla Fire TV.
Licenza e attribuzione originali: CC BY-NC-SA 4.0.

Telecomando: dalla lista canali premere **Sinistra una volta** per il menu in
alto. **Giù** torna alla lista conservando
il canale selezionato. Dal video: **Indietro → Sinistra**. Nel menu,
Sinistra/Destra cambia sezione.

## Come arrivano gli aggiornamenti

Il controllo giornaliero segue le versioni pubblicate dall'autore per Kodi 21.
Prepara l'integrazione sul ramo `updates/arctic-VERSIONE`, preservando le
personalizzazioni del ramo `home-tv`. Se ci sono conflitti si ferma e li segnala.
L'apertura di una PR dipende dai permessi GitHub; il ramo e il confronto restano
comunque disponibili. Non effettua merge o installazioni automatiche.

Solo dopo le verifiche reali si pubblica il pacchetto nel ramo `kodi-repo`.
Kodi riceve questi pacchetti tramite il normale gestore aggiornamenti.
Una nuova versione di Kodi o dei plugin richiede verifiche di compatibilità.

## Installazione del repository

Scaricare [repository.arctic.hometv-1.0.0.zip](https://raw.githubusercontent.com/mymusicmyspace/skin.arctic.fuse.hometv/kodi-repo/repository.arctic.hometv-1.0.0.zip)
e installarlo in Kodi tramite **Add-ons → Install from zip file**.
Poi **Install from repository → Arctic Fuse Home TV Repository → Look and feel → Skin**.
Il canale attuale è limitato a Kodi 21. Non contiene profili, account o liste.

## Sviluppo e verifiche

Le sole modifiche ai file di funzionamento della skin sono Home, Startup e la
visibilità del menu sovrapposto sulla Home. Il resto segue il codice dell'autore.
Il nome e l'ID della variante vengono applicati durante la creazione del ZIP.

I workflow **Check Home TV**, **Propose Arctic updates** e
**Publish approved Home TV** sono nella sezione [Actions](https://github.com/mymusicmyspace/skin.arctic.fuse.hometv/actions).
La pubblicazione richiede la corrispondenza esatta con l'hash del pacchetto
verificato sul dispositivo; una versione pubblicata non può cambiare contenuto.

Istruzioni complete: [.hometv/README.md](https://github.com/mymusicmyspace/skin.arctic.fuse.hometv/blob/home-tv/.hometv/README.md).
