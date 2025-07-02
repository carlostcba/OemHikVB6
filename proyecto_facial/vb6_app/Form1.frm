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
      TabIndex        =   10
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CommandButton cmdActualizar 
      Caption         =   "Actualizar"
      Height          =   495
      Left            =   8760
      TabIndex        =   9
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
      TabIndex        =   8
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CommandButton cmdGuardar 
      Caption         =   "Guardar"
      Height          =   495
      Left            =   5880
      TabIndex        =   7
      Top             =   6000
      Width           =   1335
   End
   Begin VB.CheckBox chkActivo 
      Height          =   375
      Left            =   7080
      TabIndex        =   4
      Top             =   4800
      Width           =   255
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
      Top             =   4080
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
      TabIndex        =   11
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
      TabIndex        =   6
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
      TabIndex        =   5
      Top             =   4800
      Width           =   975
   End
   Begin VB.Image imgPreview 
      BorderStyle     =   1  'Fixed Single
      Height          =   3495
      Left            =   6600
      Stretch         =   -1  'True
      Top             =   240
      Width           =   2895
   End
End
Attribute VB_Name = "Form1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' =====================================
' VERSIÓN SIMPLIFICADA - SIN COMBOS, CATEGORÍAS FIJAS
' =====================================
Option Explicit

Private currentFacialID As Long
Private isEditMode As Boolean

' Controles existentes según la imagen:
' - txtFiltro (campo de búsqueda)
' - cmdBuscar (botón Buscar)
' - grdPersonas (grid con personas)
' - CommonDialog1 (para seleccionar archivos)
' - imgPreview (para mostrar imagen)
' - chkActivo (CheckBox)
' - lblFacialID (Label para mostrar ID)
' - Botones: cmdGuardar, cmdActualizar, cmdEliminar, cmdCargar
' - cmdAdjuntar (botón Adjuntar Imagen)

Private Sub Form_Load()
    On Error GoTo ErrHandler
    
    ' Conectar a base de datos
    Call Conectar(App.Path & "\videoman.udl")
    
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
    Set imgPreview.Picture = Nothing
    CommonDialog1.FileName = ""  ' Limpiar ruta de imagen
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
        ' Limpiar imagen previa al cambiar de persona
        CommonDialog1.FileName = ""
        Set imgPreview.Picture = Nothing
        
        Call CargarDatosFacialesExistentes
    End If
End Sub

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

Private Sub cmdGuardar_Click()
    Dim rs As New ADODB.Recordset
    Dim facialID As Long
    Dim personaID As Long
    Dim imgBytes() As Byte
    Dim imgPath As String
    Dim existeFacialID As Long
    
    On Error GoTo ErrHandler
    
    ' VALIDACIONES PARA CREAR
    If CommonDialog1.FileName = "" Then
        MsgBox "Debe adjuntar una imagen antes de guardar el rostro", vbExclamation, "Imagen Requerida"
        Exit Sub
    End If
    
    If grdPersonas.Row <= 0 Or grdPersonas.Rows <= 1 Then
        MsgBox "Debe seleccionar una persona de la lista", vbExclamation, "Persona Requerida"
        Exit Sub
    End If
    
    ' Validar que el archivo de imagen existe
    If Dir(CommonDialog1.FileName) = "" Then
        MsgBox "El archivo de imagen seleccionado no existe o no es accesible", vbExclamation, "Archivo No Válido"
        CommonDialog1.FileName = ""
        Set imgPreview.Picture = Nothing
        Exit Sub
    End If
    
    ' Confirmar antes de proceder
    If MsgBox("¿Está seguro de asignar este rostro a la persona seleccionada?" & vbCrLf & _
              "Persona: " & grdPersonas.TextMatrix(grdPersonas.Row, 1) & " " & grdPersonas.TextMatrix(grdPersonas.Row, 2), _
              vbQuestion + vbYesNo, "Confirmar Asignación") = vbNo Then
        Exit Sub
    End If
    
    ' Obtener PersonaID seleccionado
    personaID = CLng(grdPersonas.TextMatrix(grdPersonas.Row, 0))
    
    ' VALIDAR SI YA EXISTE UN ROSTRO PARA ESTA PERSONA
    rs.Open "SELECT FacialID FROM perface WHERE PersonaID = " & personaID, cn
    If Not rs.EOF Then
        existeFacialID = rs!facialID
        rs.Close
        
        ' Preguntar si desea actualizar el rostro existente
        If MsgBox("Esta persona ya tiene un rostro asignado (ID: " & existeFacialID & ")" & vbCrLf & _
                  "¿Desea actualizar el rostro existente?", vbQuestion + vbYesNo, "Rostro Existente") = vbYes Then
            ' Cargar el rostro existente y llamar actualizar
            currentFacialID = existeFacialID
            isEditMode = True
            lblFacialID.Caption = " " & existeFacialID
            Call cmdActualizar_Click
        End If
        Exit Sub
    End If
    rs.Close
    
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
    
    ' Iniciar transacción
    cn.BeginTrans
    
    ' 1. Insertar registro en face
    rs.Open "SELECT * FROM face WHERE 1=0", cn, adOpenDynamic, adLockOptimistic
    rs.AddNew
    rs!facialID = facialID
    rs!TemplateData = imgBytes
    rs!Activo = IIf(chkActivo.Value = vbChecked, 1, 0)
    rs.Update
    rs.Close
    
    ' 2. Insertar en perface
    cn.Execute "INSERT INTO perface (PersonaID, FacialID) VALUES (" & personaID & ", " & facialID & ")"
    
    ' 3. Insertar categorías fijas en facecatval
    ' Categoría 3, Valor 7 (Tipo de Identificación - Facial)
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & facialID & ", 3, 7)"
    
    ' Categoría 16, Valor 1 (Aplicación/Destino)
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & facialID & ", 16, 1)"
    
    ' Confirmar transacción
    cn.CommitTrans
    
    ' Actualizar interfaz
    currentFacialID = facialID
    isEditMode = True
    lblFacialID.Caption = " " & facialID
    
    ' Mensaje final
    MsgBox "¡Rostro facial guardado correctamente!" & vbCrLf & _
           "ID: " & facialID & vbCrLf & _
           "Persona: " & grdPersonas.TextMatrix(grdPersonas.Row, 1) & " " & grdPersonas.TextMatrix(grdPersonas.Row, 2) & vbCrLf & _
           "Sistema listo para reconocimiento facial.", vbInformation, "Registro Guardado"
    
    Exit Sub
ErrHandler:
    cn.RollbackTrans
    MsgBox "Error al guardar: " & Err.Description, vbCritical
End Sub

Private Sub cmdActualizar_Click()
    Dim rs As New ADODB.Recordset
    Dim imgBytes() As Byte
    Dim imgPath As String
    Dim updateImage As Boolean
    
    On Error GoTo ErrHandler
    
    ' VALIDACIONES PARA MODIFICAR
    If currentFacialID = 0 Then
        MsgBox "No hay un registro facial seleccionado para actualizar." & vbCrLf & _
               "Primero debe cargar los datos de una persona con rostro asignado.", vbExclamation, "Sin Registro Seleccionado"
        Exit Sub
    End If
    
    If Not isEditMode Then
        MsgBox "No se encuentra en modo de edición." & vbCrLf & _
               "Cargue primero un rostro existente para poder modificarlo.", vbExclamation, "Modo Edición Requerido"
        Exit Sub
    End If
    
    ' Verificar que el registro facial aún existe
    rs.Open "SELECT FacialID FROM face WHERE FacialID = " & currentFacialID, cn
    If rs.EOF Then
        rs.Close
        MsgBox "El registro facial ID " & currentFacialID & " ya no existe en la base de datos." & vbCrLf & _
               "Puede haber sido eliminado por otro usuario.", vbExclamation, "Registro No Encontrado"
        currentFacialID = 0
        isEditMode = False
        lblFacialID.Caption = " "
        Exit Sub
    End If
    rs.Close
    
    ' Verificar si se debe actualizar la imagen
    updateImage = (CommonDialog1.FileName <> "")
    
    If updateImage Then
        ' Validar que el archivo de imagen existe
        If Dir(CommonDialog1.FileName) = "" Then
            MsgBox "El archivo de imagen seleccionado no existe o no es accesible", vbExclamation, "Archivo No Válido"
            CommonDialog1.FileName = ""
            Exit Sub
        End If
    End If
    
    ' Confirmar antes de proceder
    Dim mensaje As String
    mensaje = "¿Está seguro de actualizar el registro facial ID: " & currentFacialID & "?" & vbCrLf
    If updateImage Then
        mensaje = mensaje & "Se actualizará la imagen y el estado activo."
    Else
        mensaje = mensaje & "Se actualizará solo el estado activo (sin cambiar imagen)."
    End If
    
    If MsgBox(mensaje, vbQuestion + vbYesNo, "Confirmar Actualización") = vbNo Then
        Exit Sub
    End If
    
    ' Iniciar transacción
    cn.BeginTrans
    
    ' Actualizar tabla face
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
    
    ' Actualizar facecatval con valores fijos
    cn.Execute "DELETE FROM facecatval WHERE FacialID = " & currentFacialID
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & currentFacialID & ", 3, 7)"
    cn.Execute "INSERT INTO facecatval (FacialID, CategoriaID, ValorID) VALUES (" & currentFacialID & ", 16, 1)"
    
    ' Confirmar transacción
    cn.CommitTrans
    
    MsgBox "Registro facial actualizado correctamente.", vbInformation
    
    Exit Sub
ErrHandler:
    cn.RollbackTrans
    MsgBox "Error al actualizar: " & Err.Description, vbCritical
End Sub

Private Sub cmdEliminar_Click()
    Dim rs As New ADODB.Recordset
    Dim personaNombre As String
    
    On Error GoTo ErrHandler
    
    ' VALIDACIONES PARA ELIMINAR
    If currentFacialID = 0 Then
        MsgBox "No hay un registro facial seleccionado para eliminar." & vbCrLf & _
               "Primero debe cargar los datos de una persona con rostro asignado.", vbExclamation, "Sin Registro Seleccionado"
        Exit Sub
    End If
    
    If Not isEditMode Then
        MsgBox "No se encuentra en modo de edición." & vbCrLf & _
               "Cargue primero un rostro existente para poder eliminarlo.", vbExclamation, "Modo Edición Requerido"
        Exit Sub
    End If
    
    ' Verificar que el registro facial aún existe y obtener datos de la persona
    rs.Open "SELECT p.Nombre, p.Apellido FROM face f " & _
            "INNER JOIN perface pf ON f.FacialID = pf.FacialID " & _
            "INNER JOIN per p ON pf.PersonaID = p.PersonaID " & _
            "WHERE f.FacialID = " & currentFacialID, cn
    
    If rs.EOF Then
        rs.Close
        MsgBox "El registro facial ID " & currentFacialID & " ya no existe en la base de datos." & vbCrLf & _
               "Puede haber sido eliminado por otro usuario.", vbExclamation, "Registro No Encontrado"
        currentFacialID = 0
        isEditMode = False
        lblFacialID.Caption = " "
        Exit Sub
    End If
    
    personaNombre = rs!Nombre & " " & rs!Apellido
    rs.Close
    
    ' Confirmación con información detallada
    If MsgBox("¿Está COMPLETAMENTE SEGURO de eliminar el registro facial?" & vbCrLf & vbCrLf & _
              "ID Facial: " & currentFacialID & vbCrLf & _
              "Persona: " & personaNombre & vbCrLf & vbCrLf & _
              "ADVERTENCIA: Esta acción NO se puede deshacer." & vbCrLf & _
              "Se eliminarán todos los datos faciales asociados.", _
              vbCritical + vbYesNo + vbDefaultButton2, "CONFIRMAR ELIMINACIÓN") = vbNo Then
        Exit Sub
    End If
    
    ' Segunda confirmación para operaciones críticas
    If MsgBox("ÚLTIMA CONFIRMACIÓN:" & vbCrLf & _
              "¿Realmente desea proceder con la eliminación?" & vbCrLf & _
              "Esta acción es IRREVERSIBLE.", _
              vbQuestion + vbYesNo + vbDefaultButton2, "Confirmar Eliminación Final") = vbNo Then
        Exit Sub
    End If
    
    ' Iniciar transacción
    cn.BeginTrans
    
    ' Eliminar en orden inverso por integridad referencial
    cn.Execute "DELETE FROM facecatval WHERE FacialID = " & currentFacialID
    cn.Execute "DELETE FROM perface WHERE FacialID = " & currentFacialID
    cn.Execute "DELETE FROM face WHERE FacialID = " & currentFacialID
    
    ' Confirmar transacción
    cn.CommitTrans
    
    ' Limpiar interfaz
    currentFacialID = 0
    isEditMode = False
    lblFacialID.Caption = " "
    Set imgPreview.Picture = Nothing
    chkActivo.Value = vbChecked
    
    MsgBox "Registro facial eliminado correctamente.", vbInformation
    
    Exit Sub
ErrHandler:
    cn.RollbackTrans
    MsgBox "Error al eliminar: " & Err.Description, vbCritical
End Sub

Private Sub cmdCargar_Click()
    If grdPersonas.Row > 0 And grdPersonas.Rows > 1 Then
        Call CargarDatosFacialesExistentes
    Else
        MsgBox "Debe seleccionar una persona para cargar sus datos faciales", vbInformation
    End If
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
        ' No hay datos faciales - limpiar todo
        Set imgPreview.Picture = Nothing
        lblFacialID.Caption = " Sin datos"
        currentFacialID = 0
        isEditMode = False
        CommonDialog1.FileName = ""  ' Limpiar ruta de imagen
        chkActivo.Value = vbChecked  ' Reset a valor por defecto
        rs.Close
        Exit Sub
    End If
    facialID = rs!facialID
    rs.Close
    
    currentFacialID = facialID
    isEditMode = True
    lblFacialID.Caption = " " & facialID
    
    ' Cargar imagen y estado
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
            ' NO limpiar CommonDialog1.FileName aquí porque queremos mantener la imagen cargada
        Else
            Set imgPreview.Picture = Nothing
            CommonDialog1.FileName = ""
        End If
        chkActivo.Value = IIf(rs!Activo = 1, vbChecked, vbUnchecked)
    End If
    rs.Close
    
    Exit Sub
ErrHandler:
    MsgBox "Error al cargar datos faciales: " & Err.Description, vbCritical
    currentFacialID = 0
    isEditMode = False
    CommonDialog1.FileName = ""
End Sub

' EVENTOS
Private Sub txtFiltro_KeyPress(KeyAscii As Integer)
    If KeyAscii = 13 Then ' Enter
        Call cmdBuscar_Click
    End If
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Call Desconectar
End Sub

