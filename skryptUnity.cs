using UnityEngine;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public class WebSocketClient : MonoBehaviour
{
    [Header("Połączenie sesyjne")]
    public string serverUrl = "https://websocket-inzynierka.onrender.com";
    public string sessionCode = "";
    public bool showConnectionPanel = true;

    [Header("Elementy manipulatora")]
    public Transform[] joints;

    [Header("Ustawienia ruchu")]
    public float lerpSpeed = 10f;

    private ClientWebSocket socket;
    private CancellationTokenSource cts;
    private string token;
    private string websocketPath = "/ws/unity";
    private string status = "Wpisz kod sesji";
    private bool connecting;

    private float[] lastReceivedAngles;
    private bool newDataReceived;
    private readonly object dataLock = new object();

    [Serializable]
    private class PairRequest
    {
        public string code;
        public string role;
    }

    [Serializable]
    private class PairResponse
    {
        public string token;
        public string websocketPath;
        public string error;
    }

    [Serializable]
    private class ManipulationData
    {
        public string type;
        public float[] angles;
        public double timestamp;
        public long sequence;
    }

    private void OnGUI()
    {
        if (!showConnectionPanel)
            return;

        GUI.Box(new Rect(20, 20, 390, 180), "Połączenie z sesją manipulatora");
        GUI.Label(new Rect(40, 55, 95, 25), "Serwer:");
        serverUrl = GUI.TextField(new Rect(135, 55, 250, 25), serverUrl);
        GUI.Label(new Rect(40, 90, 95, 25), "Kod sesji:");
        sessionCode = GUI.TextField(new Rect(135, 90, 250, 25), sessionCode.ToUpperInvariant(), 9);

        GUI.enabled = !connecting && !string.IsNullOrWhiteSpace(sessionCode);
        if (GUI.Button(new Rect(135, 125, 160, 30), connecting ? "Łączenie..." : "Połącz"))
            ConnectWithSessionCode();
        GUI.enabled = true;

        GUI.Label(new Rect(40, 162, 345, 25), status);
    }

    public void ConnectWithSessionCode()
    {
        if (connecting)
            return;

        cts?.Cancel();
        cts?.Dispose();
        cts = new CancellationTokenSource();
        token = null;
        connecting = true;
        status = "Parowanie z sesją...";
        StartCoroutine(PairAndConnect());
    }

    private IEnumerator PairAndConnect()
    {
        string baseUrl = serverUrl.TrimEnd('/');
        PairRequest requestData = new PairRequest
        {
            code = sessionCode.Trim(),
            role = "unity"
        };
        byte[] body = Encoding.UTF8.GetBytes(JsonUtility.ToJson(requestData));

        using (UnityWebRequest request = new UnityWebRequest(baseUrl + "/api/sessions/pair", "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(body);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                PairResponse errorResponse = JsonUtility.FromJson<PairResponse>(request.downloadHandler.text);
                status = errorResponse != null && !string.IsNullOrEmpty(errorResponse.error)
                    ? "Błąd: " + errorResponse.error
                    : "Błąd parowania: " + request.error;
                connecting = false;
                yield break;
            }

            PairResponse response = JsonUtility.FromJson<PairResponse>(request.downloadHandler.text);
            token = response.token;
            websocketPath = string.IsNullOrEmpty(response.websocketPath)
                ? "/ws/unity"
                : response.websocketPath;
        }

        _ = RunConnectionLoop(cts.Token);
    }

    private async Task RunConnectionLoop(CancellationToken cancellationToken)
    {
        int delaySeconds = 1;
        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                socket?.Dispose();
                socket = new ClientWebSocket();
                status = "Łączenie z WebSocket...";
                await socket.ConnectAsync(BuildWebSocketUri(), cancellationToken);
                status = "Połączono z sesją";
                connecting = false;
                delaySeconds = 1;
                await ReceiveLoop(socket, cancellationToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception exception)
            {
                status = "Rozłączono: " + exception.Message;
                connecting = false;
            }
            finally
            {
                socket?.Dispose();
                socket = null;
            }

            if (!cancellationToken.IsCancellationRequested)
            {
                status = "Ponowne łączenie za " + delaySeconds + " s";
                try
                {
                    await Task.Delay(TimeSpan.FromSeconds(delaySeconds), cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                delaySeconds = Math.Min(delaySeconds * 2, 30);
            }
        }
    }

    private Uri BuildWebSocketUri()
    {
        Uri baseUri = new Uri(serverUrl.TrimEnd('/'));
        string scheme = baseUri.Scheme == "https" ? "wss" : "ws";
        UriBuilder builder = new UriBuilder(scheme, baseUri.Host, baseUri.IsDefaultPort ? -1 : baseUri.Port)
        {
            Path = websocketPath,
            Query = "token=" + Uri.EscapeDataString(token)
        };
        return builder.Uri;
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
                    result = await activeSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer),
                        cancellationToken
                    );
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await activeSocket.CloseOutputAsync(
                            WebSocketCloseStatus.NormalClosure,
                            "closing",
                            cancellationToken
                        );
                        return;
                    }
                    messageBuffer.Write(buffer, 0, result.Count);
                }
                while (!result.EndOfMessage);

                if (result.MessageType != WebSocketMessageType.Text)
                    continue;

                string message = Encoding.UTF8.GetString(messageBuffer.ToArray());
                ManipulationData data = JsonUtility.FromJson<ManipulationData>(message);
                if (data == null || data.type != "angles" || data.angles == null || data.angles.Length != 6)
                    continue;

                lock (dataLock)
                {
                    lastReceivedAngles = data.angles;
                    newDataReceived = true;
                }
            }
        }
    }

    private void Update()
    {
        float[] angles = null;
        lock (dataLock)
        {
            if (newDataReceived)
            {
                angles = lastReceivedAngles;
                newDataReceived = false;
            }
        }

        if (angles != null)
            ApplyAnglesToModel(angles);
    }

    private void ApplyAnglesToModel(float[] angles)
    {
        int jointCount = Math.Min(joints.Length, angles.Length);
        for (int i = 0; i < jointCount; i++)
        {
            if (joints[i] == null)
                continue;

            Quaternion targetRotation = Quaternion.Euler(0, angles[i], 0);
            joints[i].localRotation = Quaternion.Slerp(
                joints[i].localRotation,
                targetRotation,
                Time.deltaTime * lerpSpeed
            );
        }
    }

    private async void OnApplicationQuit()
    {
        cts?.Cancel();
        if (socket != null && socket.State == WebSocketState.Open)
        {
            try
            {
                await socket.CloseAsync(
                    WebSocketCloseStatus.NormalClosure,
                    "closing",
                    CancellationToken.None
                );
            }
            catch
            {
                // Aplikacja jest zamykana; połączenie może już nie istnieć.
            }
        }
        socket?.Dispose();
        cts?.Dispose();
    }
}
