using UnityEngine;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public enum SessionConnectionState { Disconnected, Pairing, Connecting, Connected, Reconnecting, Failed }

public sealed class SessionConnection : MonoBehaviour
{
    public static SessionConnection Instance { get; private set; }
    public SessionConnectionState ConnectionState { get; private set; } = SessionConnectionState.Disconnected;
    public string StatusMessage { get; private set; } = "Wpisz kod sesji";
    public string ServerUrl { get; private set; } = "https://websocket-inzynierka.onrender.com";
    public event Action<SessionConnectionState, string> ConnectionStateChanged;
    public event Action<float[]> AnglesReceived;

    private readonly ConcurrentQueue<Action> mainThreadActions = new ConcurrentQueue<Action>();
    private ClientWebSocket socket;
    private CancellationTokenSource cancellation;
    private string token;
    private string websocketPath = "/ws/unity";
    private bool pairing;

    [Serializable] private class PairRequest { public string code; public string role; }
    [Serializable] private class PairResponse { public string token; public string websocketPath; public string error; }
    [Serializable] private class ManipulationData { public string type; public float[] angles; public double timestamp; public long sequence; }

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    private void Update()
    {
        while (mainThreadActions.TryDequeue(out Action action)) action.Invoke();
    }

    public static string NormalizeSessionCode(string value)
    {
        string clean = (value ?? string.Empty).Trim().ToUpperInvariant().Replace("-", string.Empty);
        if (clean.Length > 8) clean = clean.Substring(0, 8);
        return clean.Length > 4 ? clean.Substring(0, 4) + "-" + clean.Substring(4) : clean;
    }

    public static bool IsValidSessionCode(string value)
    {
        string normalized = NormalizeSessionCode(value);
        if (normalized.Length != 9 || normalized[4] != '-') return false;
        const string alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
        foreach (char character in normalized.Replace("-", string.Empty))
            if (!alphabet.Contains(character.ToString())) return false;
        return true;
    }

    public static string FriendlyError(string error)
    {
        if (string.IsNullOrWhiteSpace(error)) return "Nie udało się połączyć z serwerem.";
        if (error.Contains("invalid_or_expired_code")) return "Kod jest nieprawidłowy lub wygasł. Wygeneruj nową sesję.";
        if (error.Contains("role_already_paired")) return "Ta sesja jest już połączona z inną aplikacją Unity.";
        if (error.Contains("rate_limit_exceeded")) return "Zbyt wiele prób. Odczekaj minutę i spróbuj ponownie.";
        if (error.Contains("invalid_token")) return "Sesja utraciła ważność. Wróć do menu i użyj nowego kodu.";
        return error;
    }

    public void Connect(string code, string serverUrl)
    {
        if (pairing || ConnectionState == SessionConnectionState.Connected || ConnectionState == SessionConnectionState.Connecting) return;
        string normalizedCode = NormalizeSessionCode(code);
        if (!IsValidSessionCode(normalizedCode)) { SetState(SessionConnectionState.Failed, "Wpisz kod w formacie XXXX-XXXX."); return; }
        if (!Uri.TryCreate(serverUrl?.TrimEnd('/'), UriKind.Absolute, out Uri parsed)
            || (parsed.Scheme != Uri.UriSchemeHttp && parsed.Scheme != Uri.UriSchemeHttps))
        { SetState(SessionConnectionState.Failed, "Adres serwera musi zaczynać się od http:// lub https://."); return; }

        Disconnect();
        ServerUrl = parsed.ToString().TrimEnd('/');
        PlayerPrefs.SetString("SessionServerUrl", ServerUrl);
        PlayerPrefs.Save();
        cancellation = new CancellationTokenSource();
        pairing = true;
        SetState(SessionConnectionState.Pairing, "Sprawdzanie kodu sesji…");
        StartCoroutine(PairAndConnect(normalizedCode));
    }

    public void Disconnect()
    {
        pairing = false;
        token = null;
        cancellation?.Cancel(); cancellation?.Dispose(); cancellation = null;
        socket?.Abort(); socket?.Dispose(); socket = null;
        SetState(SessionConnectionState.Disconnected, "Rozłączono");
    }

    private IEnumerator PairAndConnect(string code)
    {
        byte[] body = Encoding.UTF8.GetBytes(JsonUtility.ToJson(new PairRequest { code = code, role = "unity" }));
        using (UnityWebRequest request = new UnityWebRequest(ServerUrl + "/api/sessions/pair", "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(body);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            request.timeout = 15;
            yield return request.SendWebRequest();
            if (request.result != UnityWebRequest.Result.Success)
            {
                PairResponse errorResponse = null;
                try { errorResponse = JsonUtility.FromJson<PairResponse>(request.downloadHandler.text); } catch { }
                pairing = false;
                string error = errorResponse != null && !string.IsNullOrEmpty(errorResponse.error) ? errorResponse.error : request.error;
                SetState(SessionConnectionState.Failed, FriendlyError(error));
                yield break;
            }
            PairResponse response = JsonUtility.FromJson<PairResponse>(request.downloadHandler.text);
            if (response == null || string.IsNullOrEmpty(response.token))
            { pairing = false; SetState(SessionConnectionState.Failed, "Serwer nie zwrócił tokenu sesji."); yield break; }
            token = response.token;
            websocketPath = string.IsNullOrEmpty(response.websocketPath) ? "/ws/unity" : response.websocketPath;
        }
        pairing = false;
        _ = RunConnectionLoop(cancellation.Token);
    }

    private async Task RunConnectionLoop(CancellationToken cancellationToken)
    {
        int delay = 1;
        bool first = true;
        while (!cancellationToken.IsCancellationRequested && !string.IsNullOrEmpty(token))
        {
            EnqueueState(first ? SessionConnectionState.Connecting : SessionConnectionState.Reconnecting,
                first ? "Łączenie z modelem…" : $"Ponowne łączenie za {delay} s…");
            if (!first)
                try { await Task.Delay(TimeSpan.FromSeconds(delay), cancellationToken); } catch (OperationCanceledException) { break; }
            try
            {
                socket?.Dispose(); socket = new ClientWebSocket();
                await socket.ConnectAsync(BuildWebSocketUri(), cancellationToken);
                EnqueueState(SessionConnectionState.Connected, "Połączono z sesją");
                first = false; delay = 1;
                await ReceiveLoop(socket, cancellationToken);
            }
            catch (OperationCanceledException) { break; }
            catch (Exception exception)
            {
                EnqueueState(SessionConnectionState.Reconnecting, "Utracono połączenie: " + exception.Message);
                first = false; delay = Math.Min(delay * 2, 30);
            }
            finally { socket?.Dispose(); socket = null; }
        }
    }

    private async Task ReceiveLoop(ClientWebSocket activeSocket, CancellationToken cancellationToken)
    {
        byte[] buffer = new byte[4096];
        while (activeSocket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
        {
            using (MemoryStream messageBuffer = new MemoryStream())
            {
                WebSocketReceiveResult result;
                do
                {
                    result = await activeSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationToken);
                    if (result.MessageType == WebSocketMessageType.Close)
                    { await activeSocket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "closing", cancellationToken); return; }
                    messageBuffer.Write(buffer, 0, result.Count);
                } while (!result.EndOfMessage);
                if (result.MessageType != WebSocketMessageType.Text) continue;
                ManipulationData data = JsonUtility.FromJson<ManipulationData>(Encoding.UTF8.GetString(messageBuffer.ToArray()));
                if (data?.type != "angles" || data.angles == null || data.angles.Length != 6) continue;
                float[] copy = (float[])data.angles.Clone();
                mainThreadActions.Enqueue(() => AnglesReceived?.Invoke(copy));
            }
        }
    }

    private Uri BuildWebSocketUri()
    {
        Uri baseUri = new Uri(ServerUrl);
        return new UriBuilder(baseUri.Scheme == Uri.UriSchemeHttps ? "wss" : "ws", baseUri.Host,
            baseUri.IsDefaultPort ? -1 : baseUri.Port) { Path = websocketPath, Query = "token=" + Uri.EscapeDataString(token) }.Uri;
    }

    private void EnqueueState(SessionConnectionState state, string message) => mainThreadActions.Enqueue(() => SetState(state, message));
    private void SetState(SessionConnectionState state, string message)
    { ConnectionState = state; StatusMessage = message; ConnectionStateChanged?.Invoke(state, message); }
    private void OnApplicationQuit() => Disconnect();
}
