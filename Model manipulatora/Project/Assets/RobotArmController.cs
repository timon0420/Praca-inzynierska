using UnityEngine;

public sealed class RobotArmController : MonoBehaviour
{
    [SerializeField] private Transform[] joints;
    [SerializeField] private float lerpSpeed = 10f;
    private float[] targetAngles;
    public Transform[] Joints { get => joints; set => joints = value; }
    public float LerpSpeed { get => lerpSpeed; set => lerpSpeed = value; }
    private void OnEnable() { if (SessionConnection.Instance != null) SessionConnection.Instance.AnglesReceived += OnAnglesReceived; }
    private void Start()
    {
        if (SessionConnection.Instance == null) { Debug.LogWarning("Uruchom aplikację od sceny MainMenuScene."); return; }
        SessionConnection.Instance.AnglesReceived -= OnAnglesReceived;
        SessionConnection.Instance.AnglesReceived += OnAnglesReceived;
    }
    private void OnDisable() { if (SessionConnection.Instance != null) SessionConnection.Instance.AnglesReceived -= OnAnglesReceived; }
    private void OnAnglesReceived(float[] angles) => targetAngles = angles;
    private void Update()
    {
        if (targetAngles == null || joints == null) return;
        int count = Mathf.Min(joints.Length, targetAngles.Length);
        for (int i = 0; i < count; i++) if (joints[i] != null)
            joints[i].localRotation = Quaternion.Slerp(joints[i].localRotation,
                Quaternion.Euler(0f, targetAngles[i], 0f), Time.deltaTime * lerpSpeed);
    }
}
