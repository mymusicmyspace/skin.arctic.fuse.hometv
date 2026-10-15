# Arctic Fuse Home TV

Variante indipendente di Arctic Fuse 3, derivata dall'opera di jurialmunkey.
ID stabile: `skin.arctic.fuse.hometv`. Licenza della skin: CC BY-NC-SA 4.0.

## Contratto degli aggiornamenti

- Non si modificano i file di `skin.arctic.fuse.3`, Estuary, Kodi o dei plugin.
- Il pacchetto include solo la skin: nessun account, lista privata o database.
- Le preferenze della variante vivono nel proprio addon_data. La copia iniziale
  della configurazione Arctic Fuse avviene solo quando il profilo della variante
  non esiste; un aggiornamento non lo ricopia e non lo sovrascrive.
- Il builder usa una base autore identificata dal suo hash. Una nuova base viene
  trattata come candidata non verificata, non come aggiornamento compatibile.
- La Home usa il percorso PVR e la riproduzione nativi di Kodi. Non apre la
  finestra PVR all'avvio, coinvolta nel crash del cambio skin osservato su 21.3.
- I file generati da Skin Variables sono cache rigenerabili. La fonte delle
  preferenze sono i JSON dei nodi nel namespace della variante.
- Gli aggiornamenti di Arctic Fuse originale non aggiornano questa variante.
  Le novità dell'autore devono essere integrate in un nuovo pacchetto verificato.

## Limiti espliciti

Conservare i dati non equivale a garantire compatibilità con software futuro.
Kodi 22 o nuovi plugin possono cambiare API, formati, dipendenze e comportamento.
Non si dichiara il supporto a una versione finché avvio, menu, canali,
riproduzione, ritorno alla Home e cambio skin non sono verificati su quella
versione. Nessuna riscrittura automatica dei plugin o adattamento non verificato.

## Riproduzione del pacchetto

`python scripts/hometv_package.py build --base PERCORSO_ZIP_AUTORE`

Il builder verifica la base contro i metadati ufficiali già conservati, rinomina
tutti i riferimenti al namespace della skin e produce un manifest SHA256.
Per valutare una base nuova usare `--candidate`: il manifest risulterà
`unverified`. Il builder non si collega alla Fire TV e non installa niente.

Backup privati del dispositivo sotto `backups/`, esclusi dalla distribuzione.
Il ripristino di emergenza deve cambiare solo `lookandfeel.skin` a
`skin.estuary`, con Kodi fermo, dopo aver salvato guisettings.xml. Non cancellare
userdata per recuperare una skin che non parte.

## Manutenzione sul dispositivo

- `python scripts/hometv_device.py status`: confronta Kodi e dipendenze con le
  versioni realmente verificate; una versione nuova risulta `unverified`.
- `python scripts/hometv_device.py install --package PACCHETTO.zip`: installazione
  o aggiornamento, consentito solo su una combinazione già verificata. Verifica
  hash, spazio, namespace e schema del profilo; salva la versione precedente e
  non ricopia le preferenze durante un aggiornamento.
- `--evaluate`: valutazione esplicita e con backup di una combinazione nuova;
  non trasforma una versione in compatibile. Solo le verifiche reali possono
  aggiungerla al registro `compatibility.json`.
- `python scripts/hometv_device.py recover`: ritorno di emergenza a Estuary/Home
  senza cancellare preferenze, canali, credenziali o database.

Gli strumenti usano ADB configurato privatamente nel progetto. Il pacchetto
richiede comunque i normali add-on dichiarati dalla skin e le verifiche di
compatibilità del gestore Kodi. Non disattiva gli aggiornamenti dei plugin.
