using UnityEngine;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using System.Text;
using System;
using Unity.VisualScripting;
using System.Collections;


public class WebSocketClient : MonoBehaviour
{
    private ClientWebSocket socket;
    private string uri = "ws://localhost:8080/ws";
    private CancellationTokenSource cts = new CancellationTokenSource();

    [Header("Elementy Manipulatora")]
    [Tooltip("Obiekty manipulatora")]
    public Transform[] joints;

    [Header("Ustawienia Ruchu")]
    public float lerpSpeed = 10f;
    

    [Serializable]
    public class ManipulationData
    {
        public float[] angles;
    }

    private float[] lastReceivedAngles;
    private bool newDataReceived = false;
    private readonly object lockObj = new object();

    async void Start()
    {
        socket = new ClientWebSocket();
        try
        {
            await socket.ConnectAsync(new Uri(uri), CancellationToken.None);
            Debug.Log("Connected");
            while (socket.State == WebSocketState.Open)
            {
                byte[] buffer = new byte[1024];
                var result = await socket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                string message = Encoding.UTF8.GetString(buffer, 0, result.Count);

                ManipulationData data = JsonUtility.FromJson<ManipulationData>(message);

                if (data != null && data.angles.Length == 6)
                {
                    lock (lockObj)
                    {
                        lastReceivedAngles = data.angles;
                        newDataReceived = true;
                    }
                }
            }
        } catch (Exception e)
        {
            Debug.Log(e);
        }
    }

    void Update()
    {
        if (newDataReceived)
        {
            lock (lockObj)
            {
                ApplyAnglesToModel(lastReceivedAngles);
                newDataReceived = false;
            }
        }
    }

    void ApplyAnglesToModel(float[] angles)
    {
        Debug.Log("Angles: " + angles[0] + ", " + angles[1] + ", " + angles[2] + ", " + angles[3] + ", " + angles[4] + ", " + angles[5]);

        for (int i = 0; i < joints.Length; i++)
        {
            if (joints[i] == null) continue;

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
        if (socket != null) 
            await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
    }
}
