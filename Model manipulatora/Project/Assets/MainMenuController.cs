using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

[RequireComponent(typeof(UIDocument))]
public sealed class MainMenuController : MonoBehaviour
{
    private const string DefaultServer = "https://websocket-inzynierka.onrender.com";
    private TextField codeField, serverField;
    private Label statusLabel;
    private VisualElement statusDot, advancedPanel;
    private Button connectButton, startButton;
    private bool updatingCode;

    private void OnEnable()
    {
        VisualElement root = GetComponent<UIDocument>().rootVisualElement;
        codeField = root.Q<TextField>("session-code"); serverField = root.Q<TextField>("server-url");
        statusLabel = root.Q<Label>("status-label"); statusDot = root.Q<VisualElement>("status-dot");
        advancedPanel = root.Q<VisualElement>("advanced-panel"); connectButton = root.Q<Button>("connect-button");
        startButton = root.Q<Button>("start-button");
        serverField.value = PlayerPrefs.GetString("SessionServerUrl", DefaultServer);
        codeField.maxLength = 9; startButton.SetEnabled(false); advancedPanel.style.display = DisplayStyle.None;
        codeField.RegisterValueChangedCallback(OnCodeChanged);
        connectButton.clicked += Connect; startButton.clicked += StartGame;
        root.Q<Button>("advanced-button").clicked += ToggleAdvanced; root.Q<Button>("quit-button").clicked += Quit;
        root.RegisterCallback<KeyDownEvent>(OnKeyDown);
        EnsureConnection();
        SessionConnection.Instance.ConnectionStateChanged += OnConnectionStateChanged;
        OnConnectionStateChanged(SessionConnection.Instance.ConnectionState, SessionConnection.Instance.StatusMessage);
        codeField.Focus();
    }

    private void OnDisable()
    { if (SessionConnection.Instance != null) SessionConnection.Instance.ConnectionStateChanged -= OnConnectionStateChanged; }
    private static void EnsureConnection()
    { if (SessionConnection.Instance == null) new GameObject("SessionConnection").AddComponent<SessionConnection>(); }
    private void OnCodeChanged(ChangeEvent<string> change)
    { if (updatingCode) return; updatingCode = true; codeField.SetValueWithoutNotify(SessionConnection.NormalizeSessionCode(change.newValue)); updatingCode = false; }
    private void Connect() => SessionConnection.Instance.Connect(codeField.value, serverField.value);
    private void StartGame()
    { if (SessionConnection.Instance.ConnectionState == SessionConnectionState.Connected) SceneManager.LoadScene("OutdoorsScene"); }
    private void ToggleAdvanced() => advancedPanel.style.display = advancedPanel.style.display == DisplayStyle.None ? DisplayStyle.Flex : DisplayStyle.None;
    private void OnKeyDown(KeyDownEvent evt)
    {
        if (evt.keyCode == KeyCode.Return || evt.keyCode == KeyCode.KeypadEnter) { Connect(); evt.StopPropagation(); }
        else if (evt.keyCode == KeyCode.Escape) advancedPanel.style.display = DisplayStyle.None;
    }
    private void OnConnectionStateChanged(SessionConnectionState state, string message)
    {
        statusLabel.text = message; statusDot.ClearClassList(); statusDot.AddToClassList("status-dot");
        statusDot.AddToClassList("status-" + state.ToString().ToLowerInvariant());
        bool busy = state == SessionConnectionState.Pairing || state == SessionConnectionState.Connecting;
        connectButton.SetEnabled(!busy); connectButton.text = busy ? "ŁĄCZENIE…" : "POŁĄCZ Z SESJĄ";
        startButton.SetEnabled(state == SessionConnectionState.Connected);
    }
    private static void Quit()
    { Application.Quit();
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#endif
    }
}
