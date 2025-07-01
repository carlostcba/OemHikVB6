Attribute VB_Name = "Module1"
' =====================================
' MÓDULO: modConexion.bas
' =====================================
Option Explicit

Public cn As ADODB.Connection

Public Sub Conectar(ByVal udlPath As String)
    On Error GoTo ErrHandler
    Set cn = New ADODB.Connection
    cn.ConnectionString = "File Name=" & udlPath
    cn.Open
    Exit Sub
ErrHandler:
    MsgBox "Error al conectar a la base de datos: " & Err.Description, vbCritical
End Sub

Public Sub Desconectar()
    On Error Resume Next
    If Not cn Is Nothing Then
        If cn.State = adStateOpen Then cn.Close
        Set cn = Nothing
    End If
End Sub
