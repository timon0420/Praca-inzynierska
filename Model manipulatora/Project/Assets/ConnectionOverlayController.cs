using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

[RequireComponent(typeof(UIDocument))]
public sealed class ConnectionOverlayController : MonoBehaviour
{
    private VisualElement overlay; private Label message, badge;
    private void OnEnable()
    {
        VisualElement root = GetComponent<UIDocument>().rootVisualElement;
        overlay = root.Q<VisualElement>("reconnect-overlay"); message = root.Q<Label>("reconnect-message");
        badge = root.Q<Label>("connection-badge"); root.Q<Button>("return-menu-button").clicked += ReturnToMenu;
        if (SessionConnection.Instance == null)
        { overlay.style.display = DisplayStyle.Flex; message.text = "Brak aktywnej sesji"; badge.text = "ROZŁĄCZONO"; return; }
        SessionConnection.Instance.ConnectionStateChanged += OnStateChanged;
        OnStateChanged(SessionConnection.Instance.ConnectionState, SessionConnection.Instance.StatusMessage);
    }
    private void OnDisable() { if (SessionConnection.Instance != null) SessionConnection.Instance.ConnectionStateChanged -= OnStateChanged; }
    private void OnStateChanged(SessionConnectionState state, string status)
    {
        bool connected = state == SessionConnectionState.Connected;
        overlay.style.display = connected ? DisplayStyle.None : DisplayStyle.Flex;
        message.text = status; badge.text = connected ? "POŁĄCZONO" : "PONOWNE ŁĄCZENIE";
        badge.EnableInClassList("badge-online", connected);
    }
    private static void ReturnToMenu() { SessionConnection.Instance?.Disconnect(); SceneManager.LoadScene("MainMenuScene"); }
}
