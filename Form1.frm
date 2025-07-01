VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "MSFlxGrd.ocx"
Object = "{F9043C88-F6F2-101A-A3C9-08002B2F49FB}#1.2#0"; "ComDlg32.OCX"
Begin VB.Form Form1 
   Caption         =   "Valor:"
   ClientHeight    =   6705
   ClientLeft      =   60
   ClientTop       =   405
   ClientWidth     =   10545
   LinkTopic       =   "Form1"
   ScaleHeight     =   6705
   ScaleWidth      =   10545
   StartUpPosition =   3  'Windows Default
   Begin VB.CommandButton cmdEliminar 
      Caption         =   "Eliminar"
      Height          =   495
      Left            =   3960
      TabIndex        =   14
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CommandButton cmdActualizar 
      Caption         =   "Actualizar"
      Height          =   495
      Left            =   8760
      TabIndex        =   13
      Top             =   6000
      Width           =   1335
   End
   Begin MSComDlg.CommonDialog CommonDialog1 
      Left            =   240
      Top             =   6000
      _ExtentX        =   847
      _ExtentY        =   847
      _Version        =   393216
   End
   Begin VB.CommandButton cmdCargar 
      Caption         =   "Cargar"
      Height          =   495
      Left            =   7320
      TabIndex        =   12
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CommandButton cmdGuardar 
      Caption         =   "Guardar"
      Height          =   495
      Left            =   5880
      TabIndex        =   11
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CheckBox chkActivo 
      Height          =   375
      Left            =   7080
      TabIndex        =   6
      Top             =   4800
      Width           =   255
   End
   Begin VB.ComboBox cmbValor 
      Height          =   315
      Left            =   7080
      TabIndex        =   5
      Top             =   4320
      Width           =   3015
   End
   Begin VB.ComboBox cmbCategoria 
      Height          =   315
      Left            =   7080
      TabIndex        =   4
      Top             =   3840
      Width           =   3015
   End
   Begin VB.CommandButton cmdAdjuntar 
      Caption         =   "Adjuntar Imagen"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   5880
      TabIndex        =   3
      Top             =   3120
      Width           =   4215
   End
   Begin MSFlexGridLib.MSFlexGrid grdPersonas 
      Height          =   4695
      Left            =   120
      TabIndex        =   2
      Top             =   840
      Width           =   5295
      _ExtentX        =   9340
      _ExtentY        =   8281
      _Version        =   393216
   End
   Begin VB.CommandButton cmdBuscar 
      Caption         =   "Buscar"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   3840
      TabIndex        =   1
      Top             =   240
      Width           =   1455
   End
   Begin VB.TextBox txtFiltro 
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   405
      Left            =   120
      TabIndex        =   0
      Top             =   240
      Width           =   3495
   End
   Begin VB.Label Label4 
      Caption         =   "Facial ID :"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   5880
      TabIndex        =   15
      Top             =   5280
      Width           =   975
   End
   Begin VB.Label lblFacialID 
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   7080
      TabIndex        =   10
      Top             =   5280
      Width           =   3015
   End
   Begin VB.Label Label3 
      Caption         =   "Activo"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   5880
      TabIndex        =   9
      Top             =   4800
      Width           =   975
   End
   Begin VB.Label Label2 
      Caption         =   "Valor :"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   255
      Left            =   5880
      TabIndex        =   8
      Top             =   4320
      Width           =   975
   End
   Begin VB.Label Label1 
      Caption         =   "Categoria :"
      BeginProperty Font 
         Name            =   "Calibri"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   5880
      TabIndex        =   7
      Top             =   3840
      Width           =   975
   End
   Begin VB.Image imgPreview 
      BorderStyle     =   1  'Fixed Single
      Height          =   2655
      Left            =   6960
      Stretch         =   -1  'True
      Top             =   240
      Width           =   2175
   End
End
Attribute VB_Name = "Form1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' =====================================
' VERSIÓN SIMPLIFICADA - SOLO CONTROLES QUE SABEMOS QUE EXISTEN
' =====================================
Option Explicit

Private currentFacialID As Long
Private isEditMode As Boolean

' Basándome en las imágenes, estos son los controles que veo que existen:
' - txtFiltro (campo de búsqueda)
' - cmdBuscar (botón Buscar)
' - grdPersonas (grid con personas)
' - CommonDialog1 (para seleccionar archivos)
' - imgPreview (para mostrar imagen)
' - cmbCategoria y cmbValor (ComboBoxes)
' - chkActivo (CheckBox)
' - lblFacialID (Label para mostrar ID)
' - Botones: cmdGuardar, cmdActualizar, cmdEliminar, cmdCargar

Private Sub Form_Load()
    On Error GoTo ErrHandler
    
    ' Conectar a base de datos
    Call Conectar(App.Path & "\videoman.udl")
    
    ' Cargar ComboBox desde catval
    Call CargarCategorias
    
    ' Inicializar controles
    Call InicializarControles
    
    Exit Sub
ErrHandler:
    MsgBox "Error al inicializar la aplicación: " & Err.Description, vbCritical
End Sub

Private Sub InicializarControles()
    ' Configurar grid de personas
    With grdPersonas
        .Clear
        .Rows = 1
        .Cols = 3
        .TextMatrix(0, 0) = "ID"
        .TextMatrix(0, 1) = "Nombre"
        .TextMatrix(0, 2) = "Apellido"
        .ColWidth(0) = 800
        .ColWidth(1) = 2000
        .ColWidth(2) = 2000
    End With
    
    ' Limpiar campos
    txtFiltro.Text = ""
    lblFacialID.Caption = " "
    currentFacialID = 0
    isEditMode = False
    chkActivo.Value = vbChecked
End Sub

Private Sub CargarCategorias()
    Dim rs As New ADODB.Recordset
    On Error GoTo ErrHandler
    
    cmbCategoria.Clear
    rs.Open "SELECT DISTINCT CategoriaID FROM catval WHERE CategoriaID IN (3, 16) ORDER BY CategoriaID", cn
    
    Do Until rs.EOF
        Dim categoriaID As Long
        categoriaID = rs!categoriaID
        
        Select Case categoriaID
            Case 3:
                cmbCategoria.AddItem "Tipo de Identificación"
                cmbCategoria.ItemData(cmbCategoria.NewIndex) = categoriaID
            Case 16:
                cmbCategoria.AddItem "Aplicación/Destino"
                cmbCategoria.ItemData(cmbCategoria.NewIndex) = categoriaID
        End Select
        
        rs.MoveNext
    Loop
    
    rs.Close
    Set rs = Nothing
    Exit Sub
ErrHandler:
    MsgBox "Error al cargar categorías: " & Err.Description, vbCritical
End Sub

Private Sub CargarValores(ByVal categoriaID As Long)
    Dim rs As New ADODB.Recordset
    On Error GoTo ErrHandler
    
    cmbValor.Clear
    rs.Open "SELECT ValorID, Nombre FROM catval WHERE CategoriaID = " & categoriaID & " ORDER BY ValorID", cn
    
    Do Until rs.EOF
        cmbValor.AddItem rs!Nombre
        cmbValor.ItemData(cmbValor.NewIndex) = rs!ValorID
        rs.MoveNext
    Loop
    
    rs.Close
    Set rs = Nothing
    Exit Sub
ErrHandler:
    MsgBox "Error al cargar valores para la categoría " & categoriaID & ": " & Err.Description, vbCritical
End Sub

Private Sub cmdBuscar_Click()
    Dim rs As New ADODB.Recordset
    Dim sql As String
    On Error GoTo ErrHandler
    
    If Trim(txtFiltro.Text) = "" Then
        MsgBox "Ingrese un filtro para buscar", vbInformation
        txtFiltro.SetFocus
        Exit Sub
    End If
    
    sql = "SELECT PersonaID, Nombre, Apellido FROM dbo.per WHERE Nombre LIKE '%" & txtFiltro.Text & "%' OR Apellido LIKE '%" & txtFiltro.Text & "%'"
    rs.Open sql, cn, adOpenStatic, adLockReadOnly
    
    With grdPersonas
        .Clear
        .Rows = 1
        .Cols = 3
        .TextMatrix(0, 0) = "ID"
        .TextMatrix(0, 1) = "Nombre"
        .TextMatrix(0, 2) = "Apellido"
        
        Do Until rs.EOF
            .AddItem rs!personaID & vbTab & rs!Nombre & vbTab & rs!Apellido
            rs.MoveNext
        Loop
    End With
    
    rs.Close
    Set rs = Nothing
    
    If grdPersonas.Rows > 1 Then
        MsgBox "Se encontraron " & (grdPersonas.Rows - 1) & " personas", vbInformation
    Else
        MsgBox "No se encontraron personas con ese criterio", vbInformation
    End If
    
    Exit Sub
ErrHandler:
    MsgBox "Error en la búsqueda: " & Err.Description, vbCritical
End Sub

Private Sub grdPersonas_Click()
    If grdPersonas.Row > 0 And grdPersonas.Rows > 1 Then
        Call CargarDatosFacialesExistentes
    End If
End Sub

' BOTÓN ADJUNTAR SIMPLIFICADO
Private Sub cmdAdjuntar_Click()
    On Error GoTo ErrHandler
    
    With CommonDialog1
        .Filter = "Imágenes|*.jpg;*.bmp;*.png"
        .ShowOpen
        If .FileName <> "" Then
            imgPreview.Picture = LoadPicture(.FileName)
            MsgBox "Imagen cargada correctamente", vbInformation
        End If
    End With
    
    Exit Sub
ErrHandler:
    If Err.Number <> 32755 Then ' 32755 = Cancel button
        MsgBox "Error al adjuntar imagen: " & Err.Description, vbCritical
    End If
End Sub

' =====================================
' MÉTODO ALTERNATIVO - SIN PARÁMETROS ADODB
' Si sigues teniendo problemas, usa este método más simple
' =====================================

Private Sub cmdGuardar_Click()
    Dim rs As New ADODB.Recordset
    Dim facialID As Long
    Dim personaID As Long
    Dim imgBytes() As Byte
    Dim imgPath As String
    
    On Error GoTo ErrHandler
    
    ' Validaciones
    If CommonDialog1.FileName = "" Then
        MsgBox "Debe adjuntar una imagen", vbInformation
        Exit Sub
    End If
    
    If cmbCategoria.ListIndex = -1 Or cmbValor.ListIndex = -1 Then
        MsgBox "Debe seleccionar categoría y valor", vbInformation
        Exit Sub
    End If
    
    If grdPersonas.Row <= 0 Or grdPersonas.Rows <= 1 Then
        MsgBox "Debe seleccionar una persona", vbInformation
        Exit Sub
    End If
    
    ' Obtener PersonaID seleccionado
    personaID = CLng(grdPersonas.TextMatrix(grdPersonas.Row, 0))
    
    ' Obtener nuevo FacialID
    rs.Open "SELECT ISNULL(MAX(FacialID), 0) + 1 AS NuevoID FROM dbo.face", cn
    facialID = rs!NuevoID
    rs.Close
    
    ' Convertir imagen a binario
    imgPath = CommonDialog1.FileName
    Open imgPath For Binary As #1
        ReDim imgBytes(LOF(1) - 1)
        Get #1, , imgBytes
    Close #1
    
    ' MÉTODO ALTERNATIVO: Usar Recordset en lugar de Command
    cn.BeginTrans
    
    ' 1. Insertar registro en face usando Recordset
    rs.Open "SELECT * FROM face WHERE 1=0", cn, adOpenDynamic, adLockOptimistic
    rs.AddNew
    rs!facialID = facialID
    rs!TemplateData = imgBytes
    rs!Activo = IIf(chkActivo.Value = vbChecked, 1, 0)
    rs.Update
    rs.Close
    
    ' 2. Insertar en perface usando SQL directo
    cn.Execute "INSERT INTO perface (PersonaID, FacialID) VALUES (" & personaID & ", " & facialID & ")"
    
    ' 3. Insertar en facecatval usando SQL directo
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & facialID & ", " & cmbCategoria.ItemData(cmbCategoria.ListIndex) & ", " & cmbValor.ItemData(cmbValor.ListIndex) & ")"
    
    ' Confirmar transacción
    cn.CommitTrans
    
    ' Actualizar interfaz
    currentFacialID = facialID
    isEditMode = True
    lblFacialID.Caption = " " & facialID
    
    ' Mensaje personalizado
    Dim mensajeFinal As String
    If cmbCategoria.ItemData(cmbCategoria.ListIndex) = 3 And cmbValor.Text = "Facial" Then
        mensajeFinal = "¡Imagen facial guardada correctamente!" & vbCrLf & _
                      "ID: " & facialID & vbCrLf & _
                      "Tipo: Identificación Facial" & vbCrLf & _
                      "Sistema listo para reconocimiento facial."
    Else
        mensajeFinal = "Imagen guardada correctamente con ID: " & facialID & vbCrLf & _
                      "Tipo: " & cmbValor.Text
    End If
    
    MsgBox mensajeFinal, vbInformation, "Registro Guardado"
    
    Exit Sub
ErrHandler:
    cn.RollbackTrans
    MsgBox "Error al guardar: " & Err.Description, vbCritical
End Sub

' =====================================
' MÉTODO ALTERNATIVO PARA ACTUALIZAR
' =====================================
Private Sub cmdActualizar_Click()
    Dim rs As New ADODB.Recordset
    Dim imgBytes() As Byte
    Dim imgPath As String
    Dim updateImage As Boolean
    
    On Error GoTo ErrHandler
    
    If currentFacialID = 0 Then
        MsgBox "No hay un registro facial seleccionado para actualizar", vbInformation
        Exit Sub
    End If
    
    If cmbCategoria.ListIndex = -1 Or cmbValor.ListIndex = -1 Then
        MsgBox "Debe seleccionar categoría y valor", vbInformation
        Exit Sub
    End If
    
    ' Verificar si se debe actualizar la imagen
    updateImage = (CommonDialog1.FileName <> "")
    
    ' Iniciar transacción
    cn.BeginTrans
    
    ' Actualizar tabla face usando Recordset
    rs.Open "SELECT * FROM face WHERE FacialID = " & currentFacialID, cn, adOpenDynamic, adLockOptimistic
    If Not rs.EOF Then
        If updateImage Then
            ' Convertir imagen a binario
            imgPath = CommonDialog1.FileName
            Open imgPath For Binary As #1
                ReDim imgBytes(LOF(1) - 1)
                Get #1, , imgBytes
            Close #1
            rs!TemplateData = imgBytes
        End If
        rs!Activo = IIf(chkActivo.Value = vbChecked, 1, 0)
        rs.Update
    End If
    rs.Close
    
    ' Actualizar facecatval
    cn.Execute "DELETE FROM facecatval WHERE FacialID = " & currentFacialID
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & currentFacialID & ", " & cmbCategoria.ItemData(cmbCategoria.ListIndex) & ", " & cmbValor.ItemData(cmbValor.ListIndex) & ")"
    
    ' Confirmar transacción
    cn.CommitTrans
    
    MsgBox "Registro facial actualizado correctamente.", vbInformation
    
    Exit Sub
ErrHandler:
    cn.RollbackTrans
    MsgBox "Error al actualizar: " & Err.Description, vbCritical
End Sub

Private Sub CargarDatosFacialesExistentes()
    Dim personaID As Long
    
    If grdPersonas.Row <= 0 Then Exit Sub
    
    personaID = CLng(grdPersonas.TextMatrix(grdPersonas.Row, 0))
    Call CargarDatosFaciales(personaID)
End Sub

Private Sub CargarDatosFaciales(ByVal personaID As Long)
    Dim rs As New ADODB.Recordset
    Dim bytes() As Byte
    Dim tmpPath As String
    Dim facialID As Long
    
    On Error GoTo ErrHandler

    ' Obtener FacialID más reciente
    rs.Open "SELECT TOP 1 FacialID FROM perface WHERE PersonaID = " & personaID & " ORDER BY FacialID DESC", cn
    If rs.EOF Then
        ' No hay datos faciales
        Set imgPreview.Picture = Nothing
        lblFacialID.Caption = " Sin datos"
        currentFacialID = 0
        rs.Close
        Exit Sub
    End If
    facialID = rs!facialID
    rs.Close
    
    currentFacialID = facialID
    lblFacialID.Caption = " " & facialID
    
    ' Cargar imagen
    rs.Open "SELECT TemplateData, Activo FROM face WHERE FacialID = " & facialID, cn
    If Not rs.EOF Then
        If Not IsNull(rs!TemplateData) Then
            bytes = rs!TemplateData
            tmpPath = App.Path & "\temp_img.jpg"
            Open tmpPath For Binary As #1
                Put #1, , bytes
            Close #1
            imgPreview.Picture = LoadPicture(tmpPath)
            Kill tmpPath
        End If
        chkActivo.Value = IIf(rs!Activo = 1, vbChecked, vbUnchecked)
    End If
    rs.Close

    ' Cargar categoría/valor
    rs.Open "SELECT CategoriaID, ValorID FROM facecatval WHERE FacialID = " & facialID, cn
    If Not rs.EOF Then
        ' Buscar y seleccionar categoría
        Dim i As Integer
        For i = 0 To cmbCategoria.ListCount - 1
            If cmbCategoria.ItemData(i) = rs!categoriaID Then
                cmbCategoria.ListIndex = i
                Call CargarValores(rs!categoriaID)
                Exit For
            End If
        Next
        
        ' Buscar y seleccionar valor
        For i = 0 To cmbValor.ListCount - 1
            If cmbValor.ItemData(i) = rs!ValorID Then
                cmbValor.ListIndex = i
                Exit For
            End If
        Next
    End If
    rs.Close
    
    Exit Sub
ErrHandler:
    MsgBox "Error al cargar datos faciales: " & Err.Description, vbCritical
End Sub

' EVENTOS
Private Sub cmbCategoria_Click()
    If cmbCategoria.ListIndex >= 0 Then
        Call CargarValores(cmbCategoria.ItemData(cmbCategoria.ListIndex))
    End If
End Sub

Private Sub txtFiltro_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then ' Enter
        Call cmdBuscar_Click
    End If
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Call Desconectar
End Sub
