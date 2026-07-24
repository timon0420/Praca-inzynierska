# Uruchomienie systemu web → Go → Python → Unity

Aktywny system nie wymaga aplikacji desktopowej. Strona tworzy sesję, Go
automatycznie przekazuje kod i klatki do workera Python, a użytkownik wpisuje
kod wyłącznie w Unity.

## Lokalnie

W katalogu głównym projektu:

```powershell
$env:INTERNAL_SERVICE_TOKEN = "lokalny-losowy-sekret"
docker compose up --build
```

Frontend będzie dostępny pod `http://localhost:10000`, a serwer sesji pod
`http://localhost:8080`.

Sam worker można uruchomić diagnostycznie:

```powershell
cd "System sterowania"
.\env\Scripts\python.exe run.py
```

Jest to serwis HTTP na porcie `8090`, nie aplikacja desktopowa.

## Render

Plik `render.yaml` definiuje publiczny serwer Go oraz zabezpieczony worker
MediaPipe. Po utworzeniu lub zsynchronizowaniu Blueprinta Render automatycznie:

- buduje oba obrazy z właściwych katalogów monorepo,
- generuje wspólny `INTERNAL_SERVICE_TOKEN`,
- przekazuje Go wewnętrzny adres workera jako `ANALYSIS_SERVICE_HOSTPORT`.

Istniejący frontend korzysta z publicznego adresu
`https://websocket-inzynierka.onrender.com`.

Go przesyła kod sesji do workera w nagłówku `X-Session-Code`.
`X-Internal-Token` zabezpiecza endpoint `/analyze`. Kod w katalogu
`System sterowania/legacy-desktop` jest wyłącznie archiwum i nie uczestniczy
w budowaniu, testowaniu ani wdrażaniu.
