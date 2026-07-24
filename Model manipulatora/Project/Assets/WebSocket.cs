using System;
using UnityEngine;

/// <summary>
/// Tymczasowy komponent zgodności używany wyłącznie do migracji istniejącej sceny.
/// Sieć obsługuje SessionConnection, a ruch ramienia RobotArmController.
/// </summary>
[Obsolete("Use SessionConnection and RobotArmController instead.")]
public sealed class WebSocketClient : MonoBehaviour
{
    [Header("Elementy manipulatora do migracji")]
    public Transform[] joints;

    [Header("Ustawienia ruchu do migracji")]
    public float lerpSpeed = 10f;
}
