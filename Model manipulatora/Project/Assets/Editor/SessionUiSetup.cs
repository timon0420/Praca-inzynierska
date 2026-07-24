using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

public static class SessionUiSetup
{
    private const string MenuScenePath = "Assets/MainMenuScene.unity";
    private const string GameScenePath = "Assets/OutdoorsScene.unity";
    private const string PanelSettingsPath = "Assets/UI/SessionPanelSettings.asset";

    [InitializeOnLoadMethod]
    private static void BuildOnceAfterCompilation()
    {
        if (AssetDatabase.LoadAssetAtPath<SceneAsset>(MenuScenePath) == null)
            EditorApplication.delayCall += Build;
    }

    [MenuItem("Tools/Manipulator/Build Session UI")]
    public static void Build()
    {
        AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        PanelSettings panelSettings = CreateOrUpdatePanelSettings();
        CreateMenuScene(panelSettings);
        UpdateGameScene(panelSettings);
        EditorBuildSettings.scenes = new[]
        {
            new EditorBuildSettingsScene(MenuScenePath, true),
            new EditorBuildSettingsScene(GameScenePath, true)
        };
        AssetDatabase.SaveAssets();
        Debug.Log("Session UI scenes and build settings created successfully.");
    }

    private static PanelSettings CreateOrUpdatePanelSettings()
    {
        PanelSettings settings = AssetDatabase.LoadAssetAtPath<PanelSettings>(PanelSettingsPath);
        if (settings == null)
        {
            settings = ScriptableObject.CreateInstance<PanelSettings>();
            AssetDatabase.CreateAsset(settings, PanelSettingsPath);
        }
        settings.scaleMode = PanelScaleMode.ScaleWithScreenSize;
        settings.referenceResolution = new Vector2Int(1920, 1080);
        settings.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
        settings.match = 0.5f;
        settings.sortingOrder = 100;
        EditorUtility.SetDirty(settings);
        return settings;
    }

    private static void CreateMenuScene(PanelSettings panelSettings)
    {
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        GameObject connectionObject = new GameObject("SessionConnection");
        connectionObject.AddComponent<SessionConnection>();

        GameObject uiObject = new GameObject("MainMenuUI");
        UIDocument document = uiObject.AddComponent<UIDocument>();
        document.panelSettings = panelSettings;
        document.visualTreeAsset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/UI/MainMenu.uxml");
        document.sortingOrder = 0;
        uiObject.AddComponent<MainMenuController>();

        CreateEventSystem();
        EditorSceneManager.SaveScene(scene, MenuScenePath);
    }

    private static void UpdateGameScene(PanelSettings panelSettings)
    {
        Scene scene = EditorSceneManager.OpenScene(GameScenePath, OpenSceneMode.Single);
        WebSocketClient legacy = Object.FindFirstObjectByType<WebSocketClient>();
        if (legacy != null)
        {
            RobotArmController robot = legacy.GetComponent<RobotArmController>();
            if (robot == null) robot = legacy.gameObject.AddComponent<RobotArmController>();
            robot.Joints = legacy.joints;
            robot.LerpSpeed = legacy.lerpSpeed;
            Object.DestroyImmediate(legacy);
        }

        ConnectionOverlayController existingOverlay = Object.FindFirstObjectByType<ConnectionOverlayController>();
        if (existingOverlay == null)
        {
            GameObject overlayObject = new GameObject("SessionConnectionOverlay");
            UIDocument document = overlayObject.AddComponent<UIDocument>();
            document.panelSettings = panelSettings;
            document.visualTreeAsset = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/UI/ConnectionOverlay.uxml");
            document.sortingOrder = 100;
            overlayObject.AddComponent<ConnectionOverlayController>();
        }

        CreateEventSystem();
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
    }

    private static void CreateEventSystem()
    {
        if (Object.FindFirstObjectByType<EventSystem>() != null) return;
        GameObject eventSystemObject = new GameObject("EventSystem");
        eventSystemObject.AddComponent<EventSystem>();
        eventSystemObject.AddComponent<InputSystemUIInputModule>();
    }
}
