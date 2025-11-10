<?php
  // jpgsvault.php - Dynamic Folder & Image Gallery with DB + Fullscreen + Copy Link + BULK UPLOAD + EDIT/DELETE + UPLOADED FOLDERS + MOVE TO UPLOADED + **SEARCH BY URL**
  // ---------------------------------------------------------------
  // DATABASE
  $host = 'sql211.infinityfree.com';
  $dbname = 'if0_40366861_jpgsvault';
  $username = 'if0_40366861';
  $password = 'dpno6IdIwo5ShM';
  try {
      $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
      $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
  } catch (PDOException $e) {
      die("Connection failed: " . $e->getMessage());
  }
  // Ensure base table exists
  $pdo->exec("CREATE TABLE IF NOT EXISTS jpgsvault_table (id INT AUTO_INCREMENT PRIMARY KEY)");
  // ---------------------------------------------------------------
  // HELPERS
  function columnExists($pdo, $col) {
      $stmt = $pdo->prepare("SHOW COLUMNS FROM jpgsvault_table LIKE ?");
      $stmt->execute([$col]);
      return $stmt->rowCount() > 0;
  }
  function formatName($col) {
      return ucwords(str_replace('_', ' ', $col));
  }
  function getImagesInFolder($pdo, $folder) {
      $stmt = $pdo->prepare("SELECT `$folder` FROM jpgsvault_table WHERE id = 1");
      $stmt->execute();
      $json = $stmt->fetchColumn();
      return $json ? json_decode($json, true) : [];
  }
  function saveImagesToFolder($pdo, $folder, $images) {
      $json = json_encode($images);
      $pdo->prepare("UPDATE jpgsvault_table SET `$folder` = ? WHERE id = 1")
          ->execute([$json]);
  }
  function getPairedUploadedFolder($folder) {
      return $folder . '_uploaded';
  }
  function isUploadedFolder($folder) {
      return str_ends_with($folder, '_uploaded');
  }
  function getOriginalFolder($uploadedFolder) {
      return substr($uploadedFolder, 0, -9); // remove '_uploaded'
  }
  // ---------------------------------------------------------------
  // INITIAL ROW
  $pdo->prepare("INSERT IGNORE INTO jpgsvault_table (id) VALUES (1)")->execute();

  // ---------------------------------------------------------------
  // AUTO-CREATE UPLOADED COLUMN FOR EACH FOLDER
  $allColumns = [];
  $stmt = $pdo->query("SHOW COLUMNS FROM jpgsvault_table");
  while ($col = $stmt->fetch(PDO::FETCH_ASSOC)) {
      if ($col['Field'] !== 'id') {
          $allColumns[] = $col['Field'];
      }
  }

  // Create missing uploaded columns
  foreach ($allColumns as $col) {
      if (!isUploadedFolder($col)) {
          $uploaded = getPairedUploadedFolder($col);
          if (!columnExists($pdo, $uploaded)) {
              $pdo->exec("ALTER TABLE jpgsvault_table ADD COLUMN `$uploaded` JSON DEFAULT NULL");
          }
      }
  }

  // ---------------------------------------------------------------
  // CREATE FOLDER
  if (isset($_POST['action']) && $_POST['action'] === 'create_folder') {
      $folder = trim($_POST['folder_name']);
      $folder = preg_replace('/[^a-zA-Z0-9_]/', '', $folder);
      if ($folder && !columnExists($pdo, $folder)) {
          $pdo->exec("ALTER TABLE jpgsvault_table ADD COLUMN `$folder` JSON DEFAULT NULL");
          $uploaded = getPairedUploadedFolder($folder);
          $pdo->exec("ALTER TABLE jpgsvault_table ADD COLUMN `$uploaded` JSON DEFAULT NULL");
          echo json_encode(['success' => true]);
      } else {
          echo json_encode(['success' => false, 'message' => 'Invalid or existing folder']);
      }
      exit;
  }

  // ---------------------------------------------------------------
  // RENAME FOLDER
  if (isset($_POST['action']) && $_POST['action'] === 'rename_folder') {
      $old = $_POST['old_folder'];
      $new = preg_replace('/[^a-zA-Z0-9_]/', '', trim($_POST['new_name']));
      if (!$old || !$new || $old === $new || !columnExists($pdo, $old) || columnExists($pdo, $new)) {
          echo json_encode(['success' => false, 'message' => 'Invalid or existing name']);
          exit;
      }
      $pdo->exec("ALTER TABLE jpgsvault_table CHANGE `$old` `$new` JSON DEFAULT NULL");

      $oldUploaded = getPairedUploadedFolder($old);
      $newUploaded = getPairedUploadedFolder($new);
      if (columnExists($pdo, $oldUploaded)) {
          $pdo->exec("ALTER TABLE jpgsvault_table CHANGE `$oldUploaded` `$newUploaded` JSON DEFAULT NULL");
      }

      $uploadDirOld = "jpgs/$old/";
      $uploadDirNew = "jpgs/$new/";
      if (is_dir($uploadDirOld)) rename($uploadDirOld, $uploadDirNew);

      $uploadDirOldUp = "jpgs/$oldUploaded/";
      $uploadDirNewUp = "jpgs/$newUploaded/";
      if (is_dir($uploadDirOldUp)) rename($uploadDirOldUp, $uploadDirNewUp);

      echo json_encode(['success' => true, 'new_folder' => $new, 'new_name' => formatName($new)]);
      exit;
  }

  // ---------------------------------------------------------------
  // DELETE FOLDER
  if (isset($_POST['action']) && $_POST['action'] === 'delete_folder') {
      $folder = $_POST['folder'];
      if (!columnExists($pdo, $folder)) {
          echo json_encode(['success' => false]);
          exit;
      }
      // Delete main folder
      $images = getImagesInFolder($pdo, $folder);
      foreach ($images as $path) if (file_exists($path)) @unlink($path);
      $dir = "jpgs/$folder/";
      if (is_dir($dir)) { array_map('unlink', glob("$dir*.*") ?: []); @rmdir($dir); }
      $pdo->exec("ALTER TABLE jpgsvault_table DROP COLUMN `$folder`");

      // Delete uploaded folder
      $uploaded = getPairedUploadedFolder($folder);
      if (columnExists($pdo, $uploaded)) {
          $imagesUp = getImagesInFolder($pdo, $uploaded);
          foreach ($imagesUp as $path) if (file_exists($path)) @unlink($path);
          $dirUp = "jpgs/$uploaded/";
          if (is_dir($dirUp)) { array_map('unlink', glob("$dirUp*.*") ?: []); @rmdir($dirUp); }
          $pdo->exec("ALTER TABLE jpgsvault_table DROP COLUMN `$uploaded`");
      }

      echo json_encode(['success' => true]);
      exit;
  }

  // ---------------------------------------------------------------
  // BULK UPLOAD
  if (isset($_POST['action']) && $_POST['action'] === 'upload_images') {
      $folder = $_POST['folder'];
      if (!columnExists($pdo, $folder)) {
          echo json_encode(['success' => false, 'message' => 'Folder not found']);
          exit;
      }
      $uploadDir = "jpgs/$folder/";
      if (!is_dir($uploadDir)) mkdir($uploadDir, 0755, true);
      $allowed = ['jpg','jpeg','png','gif','webp','bmp','svg'];
      $uploaded = []; $errors = [];
      foreach ($_FILES['images']['name'] as $i => $name) {
          if ($_FILES['images']['error'][$i] !== UPLOAD_ERR_OK) {
              $errors[] = "$name: Upload error";
              continue;
          }
          $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
          if (!in_array($ext, $allowed)) {
              $errors[] = "$name: Invalid type";
              continue;
          }
          $tmp = $_FILES['images']['tmp_name'][$i];
          $idx = count(getImagesInFolder($pdo, $folder)) + count($uploaded);
          $filename = "card_$idx.$ext";
          $path = $uploadDir . $filename;
          if (move_uploaded_file($tmp, $path)) {
              $uploaded[] = $path;
          } else {
              $errors[] = "$name: Save failed";
          }
      }
      if (!empty($uploaded)) {
          $current = getImagesInFolder($pdo, $folder);
          $all = array_merge($current, $uploaded);
          saveImagesToFolder($pdo, $folder, $all);
      }
      $baseUrl = (isset($_SERVER['HTTPS']) ? 'https' : 'http') . "://$_SERVER[HTTP_HOST]" . dirname($_SERVER['REQUEST_URI']);
      $results = array_map(fn($p) => ['path'=>$p,'url'=>$baseUrl.'/'.$p], $uploaded);
      echo json_encode([
          'success' => !empty($uploaded),
          'uploaded' => $results,
          'errors' => $errors
      ]);
      exit;
  }

  // ---------------------------------------------------------------
  // MOVE IMAGES TO UPLOADED FOLDER (now accepts full URLs)
  if (isset($_POST['action']) && $_POST['action'] === 'move_to_uploaded') {
      $folder = $_POST['folder'];
      $urlList = $_POST['urls'] ?? '';
      $urls = array_filter(array_map('trim', explode(',', $urlList)));

      if (!columnExists($pdo, $folder) || empty($urls)) {
          echo json_encode(['success' => false, 'message' => 'Invalid request']);
          exit;
      }

      $uploadedFolder = getPairedUploadedFolder($folder);
      if (!columnExists($pdo, $uploadedFolder)) {
          echo json_encode(['success' => false, 'message' => 'Uploaded folder missing']);
          exit;
      }

      $images        = getImagesInFolder($pdo, $folder);
      $uploadedImages = getImagesInFolder($pdo, $uploadedFolder);

      $base = (isset($_SERVER['HTTPS']) ? 'https' : 'http') . "://$_SERVER[HTTP_HOST]" . dirname($_SERVER['REQUEST_URI']);
      $toMove = [];
      foreach ($urls as $url) {
          $url = trim($url);
          if (strpos($url, $base) === 0) {
              $path = urldecode(substr($url, strlen($base) + 1));
          } else {
              $path = urldecode($url);
          }
          if (in_array($path, $images)) {
              $toMove[] = $path;
          }
      }

      if (empty($toMove)) {
          echo json_encode(['success' => false, 'message' => 'No matching images found']);
          exit;
      }

      $newUploaded = array_merge($uploadedImages, $toMove);
      saveImagesToFolder($pdo, $uploadedFolder, $newUploaded);

      $remaining = array_values(array_diff($images, $toMove));
      saveImagesToFolder($pdo, $folder, $remaining);

      echo json_encode(['success' => true, 'moved' => count($toMove)]);
      exit;
  }

  // ---------------------------------------------------------------
  // DELETE IMAGES
  if (isset($_POST['action']) && $_POST['action'] === 'delete_images') {
      $folder = $_POST['folder'] ?? '';
      $paths = json_decode($_POST['paths'] ?? '[]', true);
      if (!columnExists($pdo, $folder) || !is_array($paths) || empty($paths)) {
          echo json_encode(['success'=>false]);
          exit;
      }
      $current = getImagesInFolder($pdo, $folder);
      $remaining = array_values(array_diff($current, $paths));
      saveImagesToFolder($pdo, $folder, $remaining);
      foreach ($paths as $p) {
          if (file_exists($p)) @unlink($p);
      }
      echo json_encode(['success'=>true]);
      exit;
  }

  // ---------------------------------------------------------------
  // GET IMAGES
  if (isset($_GET['action']) && $_GET['action'] === 'get_images') {
      $folder = $_GET['folder'];
      $images = columnExists($pdo, $folder) ? getImagesInFolder($pdo, $folder) : [];
      $baseUrl = (isset($_SERVER['HTTPS']) ? 'https' : 'http') . "://$_SERVER[HTTP_HOST]" . dirname($_SERVER['REQUEST_URI']);
      $withUrl = array_map(fn($p)=>['path'=>$p,'url'=>$baseUrl.'/'.$p], $images);
      echo json_encode($withUrl);
      exit;
  }

  // ---------------------------------------------------------------
  // LIST FOLDERS (MAIN + UPLOADED)
  $mainFolders = [];
  $uploadedFolders = [];
  $stmt = $pdo->query("SHOW COLUMNS FROM jpgsvault_table");
  while ($col = $stmt->fetch(PDO::FETCH_ASSOC)) {
      if ($col['Field'] !== 'id') {
          if (isUploadedFolder($col['Field'])) {
              $orig = getOriginalFolder($col['Field']);
              if (columnExists($pdo, $orig)) {
                  $uploadedFolders[] = ['name' => formatName($orig) . ' (Uploaded)', 'folder' => $col['Field'], 'original' => $orig];
              }
          } else {
              $mainFolders[] = ['name'=>formatName($col['Field']), 'folder'=>$col['Field']];
          }
      }
  }
  $folders = array_merge($mainFolders, $uploadedFolders);
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JPGS Vault - Image Gallery</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  /* ----------------- DISABLE BODY SCROLL & ENABLE DIV SCROLL ----------------- */
  html, body {
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
    font-family: 'Inter', Segoe UI, Tahoma, sans-serif;
    background: var(--bg);
    color: var(--text);
  }

  .contentsdiv {
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .contentsinnerdiv {
    flex: 1;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 3rem;
  }

  /* ----------------- VARIABLES ----------------- */
  :root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --success: #10b981;
    --danger: #ef4444;
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #1e293b;
    --text-light: #64748b;
    --border: #e2e8f0;
    --shadow: 0 10px 25px rgba(0,0,0,0.08);
    --radius: 16px;
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* ----------------- GLOBAL ----------------- */
  *{margin:0;padding:0;box-sizing:border-box}

  /* ----------------- HEADER ----------------- */
  header{
    text-align:center;
    padding:2.5rem 1rem 1.5rem;
    background:linear-gradient(135deg,var(--primary),#8b5cf6);
    color:#fff;
    border-bottom-left-radius:var(--radius);
    border-bottom-right-radius:var(--radius);
    box-shadow:var(--shadow);
    margin-bottom:-1rem;
    position:relative;
    overflow:hidden;
    flex-shrink: 0;
  }
  header::after{
    content:'';position:absolute;bottom:0;left:0;right:0;height:50px;
    background:linear-gradient(transparent,var(--bg));
  }
  header h1{font-size:2.8rem;font-weight:700;margin-bottom:.5rem;text-shadow:0 2px 10px rgba(0,0,0,.2)}
  header .subtitle{font-size:1rem;opacity:.9;font-weight:500}

  /* ----------------- CONTROLS ----------------- */
  .controls{
    background:var(--card);
    padding:1.5rem 1rem;
    border-radius:var(--radius);
    margin:1.5rem 1rem 0;
    max-width:1100px;
    box-shadow:var(--shadow);
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:1.2rem;
    position:sticky;
    top:1rem;
    z-index:10;
    backdrop-filter:blur(10px);
    border:1px solid var(--border);
    flex-shrink: 0;
  }
  .top-controls{
    display:flex;
    align-items:center;
    gap:1rem;
    flex-wrap:wrap;
    justify-content:center;
    width:100%;
  }
  .active-folder-btn{
    padding:.75rem 1.8rem;font-size:1rem;font-weight:600;
    color:white;background:var(--primary);border:none;
    border-radius:50px;cursor:default;
    box-shadow:0 4px 15px rgba(99,102,241,.3);min-width:180px;
  }
  .folder-dropdown{
    position:relative;
    display:inline-block;
  }
  .folder-toggle{
    padding:.75rem 1.5rem;font-size:.95rem;font-weight:600;
    color:var(--text-light);background:#f1f5f9;border:none;
    border-radius:50px;cursor:pointer;transition:var(--transition);
    box-shadow:0 2px 6px rgba(0,0,0,.05);min-width:140px;
  }
  .folder-toggle:hover{background:#e2e8f0}
  .folder-menu{
    position:absolute;
    top:100%;
    left:50%;
    transform:translateX(-50%);
    margin-top:.5rem;
    background:#fff;
    border-radius:12px;
    box-shadow:0 10px 30px rgba(0,0,0,.15);
    overflow:hidden;
    min-width:220px;
    z-index:20;
    display:none;
    animation:fadeIn .2s ease;
  }
  .folder-menu.show{display:block}
  .folder-item{
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:.75rem 1rem;
    border:none;
    background:none;
    font-size:.95rem;
    color:var(--text);
    cursor:pointer;
    transition:var(--transition);
    width:100%;
    text-align:left;
  }
  .folder-item:hover{background:#f8fafc}
  .folder-item .folder-name{
    flex:1;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .folder-item .folder-actions{
    display:flex;
    gap:.4rem;
  }
  .folder-actions button{
    background:none;
    border:none;
    cursor:pointer;
    font-size:1rem;
    padding:2px 4px;
    border-radius:4px;
    transition:background .2s;
  }
  .folder-actions .edit-btn{color:#f59e0b}
  .folder-actions .edit-btn:hover{background:#fffbe6}
  .folder-actions .delete-btn{color:#ef4444}
  .folder-actions .delete-btn:hover{background:#fee2e2}
  .folder-menu .create-folder-item{
    border-top:1px solid #eee;
    color:var(--primary);
    font-weight:600;
    background:#f0f9ff;
    justify-content:center;
  }
  .folder-menu .create-folder-item:hover{background:#e0f2fe}
  .folder-menu .uploaded-section{
    border-top:2px solid #ddd;
    padding-top:.5rem;
    margin-top:.5rem;
    font-weight:600;
    color:#555;
    pointer-events:none;
  }

  /* ----------------- SEARCH INPUT ----------------- */
  .search-wrapper{
    position:relative;
    flex:1;
    max-width:360px;
  }
  .search-input{
    width:100%;
    padding:.75rem 1rem .75rem 2.5rem;
    border:1px solid var(--border);
    border-radius:50px;
    font-size:.95rem;
    background:#fff;
    transition:var(--transition);
  }
  .search-input:focus{
    outline:none;
    border-color:var(--primary);
    box-shadow:0 0 0 3px rgba(99,102,241,.2);
  }
  .search-icon{
    position:absolute;
    left:12px;
    top:50%;
    transform:translateY(-50%);
    color:#94a3b8;
    pointer-events:none;
  }

  /* ----------------- SELECTION CONTROLS ----------------- */
  .selection-controls{
    display:none;
    align-items:center;
    gap:1rem;
    flex-wrap:wrap;
    justify-content:center;
    font-size:.95rem;
    color:var(--text-light);
  }
  .selection-controls label{display:flex;align-items:center;gap:.5rem;cursor:pointer}
  .selection-controls input[type=checkbox]{width:18px;height:18px;accent-color:var(--primary);cursor:pointer}
  .delete-selected-btn{
    background:var(--danger);
    color:white;
    padding:.6rem 1.2rem;
    font-size:.9rem;
    border:none;
    border-radius:50px;
    cursor:pointer;
    font-weight:600;
    display:none;
    transition:var(--transition);
  }
  .delete-selected-btn:hover{background:#dc2626;transform:translateY(-1px)}

  /* ----------------- GALLERY ----------------- */
  .gallery{
    padding:1rem 1.5rem;
    max-width:1400px;
    margin:auto;
    flex: 1;
  }
  .gallery-title{text-align:center;margin-bottom:1rem;font-size:1.5rem;color:#444}
  .images-container{
    background:#fff;
    border-radius:8px;
    padding:1rem;
    position:relative;
  }
  .image-scroll{
    overflow-x:auto;
    white-space:nowrap;
    display:flex;
    gap:1.5rem;
    align-items:flex-start;
    padding:1rem 0;
    -webkit-overflow-scrolling: touch;
  }
  .image-item{
    display:inline-block;
    text-align:center;
    position:relative;
  }
  .image-item img{
    max-height:400px;
    max-width:100%;
    border-radius:8px;
    cursor:pointer;
    box-shadow:0 4px 12px rgba(0,0,0,.1);
    transition:transform .2s;
  }
  .image-item img:hover{opacity:.9;transform:scale(1.02)}
  .image-item p{margin-top:.5rem;font-size:.9rem;color:#555}
  .empty-state,.loading,.no-results{
    text-align:center;
    padding:3rem;
    color:#888;
    font-style:italic;
  }
  .add-btn-container{text-align:center;padding:2rem}
  .add-btn-container button{
    padding:1rem 2rem;
    font-size:1.1rem;
    background:#007bff;
    color:white;
    border:none;
    border-radius:50px;
    cursor:pointer;
  }
  .add-btn-container button:hover{background:#0056b3}
  .move-to-uploaded-btn{
    margin-top:1.5rem;
    padding:.8rem 1.8rem;
    background:#10b981;
    color:white;
    border:none;
    border-radius:50px;
    font-weight:600;
    cursor:pointer;
  }
  .move-to-uploaded-btn:hover{background:#0d8b5f}

  /* ----------------- SELECTION CHECKBOX ----------------- */
  .image-item .checkbox{
    position:absolute;
    top:8px;
    left:8px;
    width:20px;
    height:20px;
    background:#fff;
    border:2px solid #ccc;
    border-radius:4px;
    opacity:0;
    transition:opacity .2s;
    cursor:pointer;
    z-index:10;
  }
  .image-item .checkbox::after{
    content:'';
    position:absolute;
    top:2px;
    left:2px;
    width:12px;
    height:12px;
    background:#007bff;
    border-radius:2px;
    opacity:0;
    transition:opacity .2s;
  }
  .image-item.selected .checkbox{opacity:1}
  .image-item.selected .checkbox::after{opacity:1}
  .image-item.selected .checkbox{border-color:#007bff}
  .image-item.selected img{outline:4px solid #007bff;outline-offset:-4px}

  /* ----------------- FAB ----------------- */
  .fab{
    position:fixed !important;
    bottom:2rem;
    right:2rem;
    background:var(--primary);
    width:56px;
    height:56px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.8rem;
    cursor:pointer;
    box-shadow:0 4px 12px rgba(0,0,0,.3);
    z-index:50;
    transition:transform .2s;
  }
  .fab:hover{transform:scale(1.1)}

  /* ----------------- MODALS ----------------- */
  .modal,.fullscreen-modal,.bulk-upload-overlay,.confirm-modal,.rename-modal,.delete-folder-modal,.move-modal{
    display:none;
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:rgba(0,0,0,.5);
    justify-content:center;
    align-items:center;
    z-index:100;
    padding:1rem;
  }
  .modal-content,.confirm-box,.bulk-upload-modal,.rename-box,.delete-folder-box,.move-box{
    background:#fff;
    padding:2rem;
    border-radius:12px;
    width:90%;
    max-width:420px;
    text-align:center;
    box-shadow:0 20px 50px rgba(0,0,0,.2);
    animation:modalPop .3s ease;
  }
  @keyframes modalPop{from{transform:scale(.9);opacity:0}to{transform:scale(1);opacity:1}}
  .modal input[type=text], .rename-box input[type=text], .move-box textarea{
    width:100%;
    padding:.8rem;
    margin:1rem 0;
    border:1px solid #ddd;
    border-radius:8px;
    font-size:1rem;
  }
  .modal button,.confirm-box button,.bulk-modal-actions button,.rename-box button,.delete-folder-box button,.move-box button{
    padding:.6rem 1.2rem;
    margin:.3rem;
    border:none;
    border-radius:50px;
    cursor:pointer;
    font-weight:600;
  }
  .modal button:first-of-type,.confirm-yes,.rename-yes,.delete-folder-yes,.move-yes{
    background:#dc3545;
    color:#fff
  }
  .modal button:last-of-type,.confirm-no,.close-bulk,.rename-no,.delete-folder-no,.move-no{
    background:#ccc;
    color:#333
  }

  /* ----------------- FULLSCREEN ----------------- */
  .fullscreen-modal{
    display:none;
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:rgba(0,0,0,.95);
    z-index:200;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    color:#fff;
  }
  .fullscreen-img{
    max-width:95%;
    max-height:80vh;
    border-radius:8px;
    box-shadow:0 0 30px rgba(0,0,0,.8);
  }
  .fullscreen-actions{
    margin-top:1.5rem;
    display:flex;
    gap:1.2rem;
    flex-wrap:wrap;
    justify-content:center;
  }
  .fullscreen-actions button{
    min-width:180px;
    padding:.8rem 1.6rem;
    font-size:1rem;
    border:none;
    border-radius:50px;
    cursor:pointer;
    font-weight:600;
    transition:background .3s;
  }
  .copy-btn{background:#17a2b8;color:white}
  .copy-btn:hover{background:#138496}
  .close-fullscreen{background:#dc3545;color:white}
  .close-fullscreen:hover{background:#c82333}
  .copied-notif{
    position:fixed;
    bottom:20px;
    left:50%;
    transform:translateX(-50%);
    background:#28a745;
    color:white;
    padding:.8rem 1.6rem;
    border-radius:50px;
    font-weight:600;
    z-index:300;
    opacity:0;
    pointer-events:none;
    transition:opacity .3s;
  }
  .copied-notif.show{opacity:1}

  /* ----------------- BULK UPLOAD ----------------- */
  .bulk-upload-modal{
    max-width:800px;
    max-height:90vh;
    overflow-y:auto
  }
  .bulk-upload-area{
    padding:2rem;
    background:#f8f9fa;
    border:2px dashed #ccc;
    border-radius:12px;
    text-align:center;
    position:relative;
  }
  .bulk-upload-area.dragover{
    background:#e3f2fd;
    border-color:#6e8efb
  }
  .bulk-file-count{
    font-weight:600;
    margin:1rem 0;
    color:#444
  }
  .bulk-preview-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(80px,1fr));
    gap:.5rem;
    max-height:300px;
    overflow-y:auto;
    padding:1rem;
    background:#fff;
    border-radius:8px;
  }
  .bulk-preview-item{position:relative}
  .bulk-preview-item img{
    width:100%;
    height:70px;
    object-fit:cover;
    border-radius:6px
  }
  .bulk-remove{
    position:absolute;
    top:2px;
    right:2px;
    background:#dc3545;
    color:white;
    width:18px;
    height:18px;
    border-radius:50%;
    font-size:10px;
    line-height:18px;
    cursor:pointer;
  }
  .bulk-progress{
    margin:1rem 0;
    display:none
  }
  .bulk-progress-bar{
    height:8px;
    background:#eee;
    border-radius:4px;
    overflow:hidden
  }
  .bulk-progress-fill{
    height:100%;
    background:#28a745;
    width:0;
    transition:width .3s
  }
  .bulk-modal-actions{
    margin-top:1.5rem;
    display:flex;
    gap:1rem;
    justify-content:center
  }

  /* ----------------- ANIMATIONS ----------------- */
  @keyframes fadeIn{
    from{opacity:0;transform:translateY(-8px)}
    to{opacity:1;transform:translateY(0)}
  }

  /* ----------------- RESPONSIVE ----------------- */
  @media(max-width:768px){
    .image-scroll{
      flex-direction:column;
      align-items:center;
      white-space:normal;
      overflow-x:hidden
    }
    .image-item img{max-height:250px}
    .fab{
      bottom:1rem;
      right:1rem;
      width:48px;
      height:48px;
      font-size:1.5rem
    }
    .fullscreen-actions{
      flex-direction:column;
      gap:1rem
    }
    .fullscreen-actions button{min-width:160px}
    .active-folder-btn{
      font-size:.9rem;
      padding:.6rem 1.2rem;
      min-width:140px
    }
    .folder-menu{
      position: fixed;
      left: 50% !important;
      transform: translateX(-50%);
      width: 90vw;
      max-width: 280px;
      min-width: 200px;
    }
    .top-controls{flex-direction:column}
    .search-wrapper{max-width:none}
  }
</style>
</head>
<body>
<div class="contentsdiv">
  <div class="contentsinnerdiv">
    <header>
      <h1>JPGS Vault</h1>
      <p class="subtitle">JPG • PNG • GIF • WEBP • BMP • SVG</p>
    </header>

    <div class="controls">
      <div class="top-controls">
        <button class="active-folder-btn" id="active-folder-btn">Select a folder</button>
        <div class="folder-dropdown">
          <button class="folder-toggle" id="folder-toggle">FOLDERS ▼</button>
          <div class="folder-menu" id="folder-menu"></div>
        </div>

        <!-- SEARCH INPUT -->
        <div class="search-wrapper">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" class="search-input" id="search-input" placeholder="Search by URL or filename...">
        </div>
      </div>

      <div class="selection-controls" id="selection-controls">
        <label><input type="checkbox" id="select-all-checkbox"> Select All</label>
        <button class="delete-selected-btn" id="delete-selected">Delete Selected (<span id="selected-count">0</span>)</button>
      </div>
    </div>

    <section class="gallery">
      <h2 class="gallery-title" id="gallery-title">Select a folder</h2>
      <div class="images-container" id="images-container">
        <div class="empty-state">Create or select a folder to begin.</div>
      </div>
      <div class="fab" id="fab-add">+</div>
    </section>

    <!-- Create Folder Modal -->
    <div class="modal" id="folder-modal">
      <div class="modal-content">
        <h3>Create New Folder</h3>
        <input type="text" id="folder-name" placeholder="e.g. Vacation 2025" maxlength="50">
        <div>
          <button id="confirm-create">Create</button>
          <button id="cancel-create">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Rename Folder Modal -->
    <div class="rename-modal" id="rename-modal">
      <div class="rename-box">
        <h3>Rename Folder</h3>
        <input type="text" id="rename-input" placeholder="New name" maxlength="50">
        <div>
          <button id="rename-yes">Rename</button>
          <button id="rename-no">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Delete Folder Confirmation Modal -->
    <div class="delete-folder-modal" id="delete-folder-modal">
      <div class="delete-folder-box">
        <p>Delete folder "<span id="delete-folder-name"></span>" and <strong>all its images</strong>?</p>
        <div>
          <button id="delete-folder-yes">Delete</button>
          <button id="delete-folder-no">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Move to Uploaded Modal -->
    <div class="move-modal" id="move-modal">
      <div class="move-box">
        <h3>Move Images to Uploaded</h3>
        <p>Enter image URLs (comma-separated) or numbers (e.g., 1, 3, 5-7):</p>
        <textarea id="move-indices" placeholder="https://..., 1, 5-8" rows="3"></textarea>
        <div>
          <button id="move-yes">Move</button>
          <button id="move-no">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Fullscreen Modal -->
    <div class="fullscreen-modal" id="fullscreen-modal">
      <img src="" alt="Full" class="fullscreen-img" id="fullscreen-img">
      <div class="fullscreen-actions">
        <button class="copy-btn" id="copy-link-btn">Copy Image Link</button>
        <button class="close-fullscreen" id="close-fullscreen">Close</button>
      </div>
    </div>

    <!-- Copied Notification -->
    <div class="copied-notif" id="copied-notif">Link copied to clipboard!</div>

    <!-- Bulk Upload Overlay -->
    <div class="bulk-upload-overlay" id="bulk-upload-overlay">
      <div class="bulk-upload-modal">
        <h3 style="margin-bottom:1rem;text-align:center">Add Images to <span id="bulk-folder-name"></span></h3>
        <div class="bulk-upload-area" id="bulk-upload-area">
          <p>Drop images or click to select (100+ supported)</p>
          <input type="file" id="bulk-input" accept="image/*" multiple style="display:none">
          <button id="bulk-choose">Choose Files</button>
          <div class="bulk-file-count" id="bulk-count">0 images selected</div>
          <div class="bulk-preview-grid" id="bulk-preview"></div>
          <div class="bulk-progress" id="bulk-progress">
            <div class="bulk-progress-bar"><div class="bulk-progress-fill" id="bulk-fill"></div></div>
            <p id="bulk-text" style="margin-top:.5rem;font-size:.9rem;color:#555"></p>
          </div>
          <div class="bulk-modal-actions">
            <button class="save-btn" id="bulk-save">Upload All</button>
            <button class="close-bulk" id="bulk-cancel">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Images Modal -->
    <div class="confirm-modal" id="confirm-modal">
      <div class="confirm-box">
        <p>Delete <span id="confirm-count">0</span> image(s)?</p>
        <button id="confirm-yes">Delete</button>
        <button id="confirm-no">Cancel</button>
      </div>
    </div>
  </div>
</div>

<script>
  const folders = <?= json_encode($folders) ?>;
  const activeBtn = document.getElementById('active-folder-btn');
  const folderToggle = document.getElementById('folder-toggle');
  const folderMenu = document.getElementById('folder-menu');
  const title = document.getElementById('gallery-title');
  const container = document.getElementById('images-container');
  const fab = document.getElementById('fab-add');
  const selectionControls = document.getElementById('selection-controls');
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  const deleteSelectedBtn = document.getElementById('delete-selected');
  const selectedCountSpan = document.getElementById('selected-count');
  const confirmModal = document.getElementById('confirm-modal');
  const confirmCount = document.getElementById('confirm-count');
  const confirmYes = document.getElementById('confirm-yes');
  const confirmNo = document.getElementById('confirm-no');
  const renameModal = document.getElementById('rename-modal');
  const renameInput = document.getElementById('rename-input');
  const renameYes = document.getElementById('rename-yes');
  const renameNo = document.getElementById('rename-no');
  const deleteFolderModal = document.getElementById('delete-folder-modal');
  const deleteFolderName = document.getElementById('delete-folder-name');
  const deleteFolderYes = document.getElementById('delete-folder-yes');
  const deleteFolderNo = document.getElementById('delete-folder-no');
  const moveModal = document.getElementById('move-modal');
  const moveUrls = document.getElementById('move-indices');
  const moveYes = document.getElementById('move-yes');
  const moveNo = document.getElementById('move-no');

  // SEARCH
  const searchInput = document.getElementById('search-input');
  let allImages = [];               // will hold the full list for the current folder
  let filteredImages = [];          // what is currently displayed
  let searchTimer = null;

  let currentFolder = null;
  let selectedImages = new Set();
  let bulkFiles = [];
  let folderToRename = null;
  let folderToDelete = null;

  // ---------- RENDER FOLDER MENU ----------
  function renderFolderMenu() {
    folderMenu.innerHTML = '';
    const createItem = document.createElement('div');
    createItem.className = 'create-folder-item folder-item';
    createItem.innerHTML = '+ Create New Folder';
    createItem.onclick = e => {
      e.stopPropagation();
      folderMenu.classList.remove('show');
      document.getElementById('folder-modal').style.display = 'flex';
    };
    folderMenu.appendChild(createItem);

    const main = folders.filter(f => !f.original);
    main.forEach(f => renderFolderItem(f));

    const uploaded = folders.filter(f => f.original);
    if (uploaded.length > 0) {
      const section = document.createElement('div');
      section.className = 'uploaded-section folder-item';
      section.innerText = 'Uploaded Collections';
      folderMenu.appendChild(section);
      uploaded.forEach(f => renderFolderItem(f, true));
    }
  }

  function renderFolderItem(f, isUploaded = false) {
    const item = document.createElement('div');
    item.className = 'folder-item';
    item.innerHTML = `
      <span class="folder-name" title="${f.name}">${f.name}</span>
      ${!isUploaded ? `<div class="folder-actions">
        <button class="edit-btn" title="Rename">Edit</button>
        <button class="delete-btn" title="Delete">Delete</button>
      </div>` : ''}
    `;
    const nameSpan = item.querySelector('.folder-name');
    nameSpan.onclick = e => {
      e.stopPropagation();
      loadFolder(f.folder, f.name);
      folderMenu.classList.remove('show');
    };
    if (!isUploaded) {
      item.querySelector('.edit-btn').onclick = e => {
        e.stopPropagation();
        folderToRename = f.folder;
        renameInput.value = f.name;
        renameModal.style.display = 'flex';
        folderMenu.classList.remove('show');
      };
      item.querySelector('.delete-btn').onclick = e => {
        e.stopPropagation();
        folderToDelete = f.folder;
        deleteFolderName.textContent = f.name;
        deleteFolderModal.style.display = 'flex';
        folderMenu.classList.remove('show');
      };
    }
    folderMenu.appendChild(item);
  }

  renderFolderMenu();

  // ---------- TOGGLE MENU ----------
  folderToggle.onclick = () => folderMenu.classList.toggle('show');
  document.addEventListener('click', e => {
    if (!folderToggle.contains(e.target) && !folderMenu.contains(e.target)) {
      folderMenu.classList.remove('show');
    }
  });

  // ---------- CREATE FOLDER ----------
  const folderModal = document.getElementById('folder-modal');
  const folderInput = document.getElementById('folder-name');
  document.getElementById('cancel-create').onclick = () => folderModal.style.display = 'none';
  document.getElementById('confirm-create').onclick = () => {
    let name = folderInput.value.trim();
    if (!name) {
      showAlert('Please enter a folder name.');
      return;
    }
    const folder = name.replace(/[^a-zA-Z0-9_]/g, '');
    fetch('', {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body: `action=create_folder&folder_name=${encodeURIComponent(folder)}`
    })
    .then(r=>r.json())
    .then(res=>{
      if (res.success) {
        const formatted = formatName(folder);
        folders.push({name: formatted, folder});
        const uploadedFolder = folder + '_uploaded';
        const uploadedName   = formatted + ' (Uploaded)';
        folders.push({name: uploadedName, folder: uploadedFolder, original: folder});
        renderFolderMenu();
        folderModal.style.display = 'none';
        loadFolder(folder, formatted);
      } else {
        showAlert(res.message||'Failed to create folder.');
      }
    });
  };

  // ---------- RENAME FOLDER ----------
  renameNo.onclick = () => { renameModal.style.display = 'none'; folderToRename = null; };
  renameYes.onclick = () => {
    const newName = renameInput.value.trim();
    if (!newName || !folderToRename) return;
    const newFolder = newName.replace(/[^a-zA-Z0-9_]/g, '');
    fetch('', {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body: `action=rename_folder&old_folder=${folderToRename}&new_name=${newFolder}`
    })
    .then(r=>r.json())
    .then(res => {
      if (res.success) {
        const idx = folders.findIndex(f => f.folder === folderToRename);
        if (idx !== -1) {
          folders[idx] = { name: res.new_name, folder: res.new_folder };
          const upIdx = folders.findIndex(f => f.original === folderToRename);
          if (upIdx !== -1) {
            folders[upIdx] = { name: res.new_name + ' (Uploaded)', folder: res.new_folder + '_uploaded', original: res.new_folder };
          }
          renderFolderMenu();
          if (currentFolder === folderToRename || currentFolder === folderToRename + '_uploaded') {
            loadFolder(res.new_folder, res.new_name);
          }
        }
      } else {
        showAlert(res.message || 'Rename failed');
      }
      renameModal.style.display = 'none';
      folderToRename = null;
    });
  };

  // ---------- DELETE FOLDER ----------
  deleteFolderNo.onclick = () => { deleteFolderModal.style.display = 'none'; folderToDelete = null; };
  deleteFolderYes.onclick = () => {
    if (!folderToDelete) return;
    fetch('', {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body: `action=delete_folder&folder=${folderToDelete}`
    })
    .then(r=>r.json())
    .then(res => {
      if (res.success) {
        folders.splice(folders.findIndex(f => f.folder === folderToDelete), 1);
        const upFolder = folderToDelete + '_uploaded';
        const upIdx = folders.findIndex(f => f.folder === upFolder);
        if (upIdx !== -1) folders.splice(upIdx, 1);
        renderFolderMenu();
        if (currentFolder === folderToDelete || currentFolder === upFolder) {
          currentFolder = null;
          activeBtn.textContent = 'Select a folder';
          title.textContent = 'Select a folder';
          container.innerHTML = '<div class="empty-state">Create or select a folder to begin.</div>';
          fab.style.display = 'none';
        }
      }
      deleteFolderModal.style.display = 'none';
      folderToDelete = null;
    });
  };

  // ---------- ALERT MODAL ----------
  const alertModal = document.createElement('div');
  alertModal.className = 'modal';
  alertModal.id = 'alert-modal';
  alertModal.innerHTML = `
    <div class="modal-content">
      <p id="alert-message"></p>
      <div><button id="alert-ok">OK</button></div>
    </div>
  `;
  document.body.appendChild(alertModal);
  const alertMessage = document.getElementById('alert-message');
  const alertOk = document.getElementById('alert-ok');
  function showAlert(msg) {
    alertMessage.textContent = msg;
    alertModal.style.display = 'flex';
  }
  alertOk.onclick = () => alertModal.style.display = 'none';

  // ---------- LOAD FOLDER ----------
  async function loadFolder(folder, name) {
    currentFolder = folder;
    activeBtn.textContent = name;
    title.textContent = `${name} Collection`;
    container.innerHTML = `<div class="loading">Loading images...</div>`;
    selectedImages.clear();
    selectionControls.style.display = 'none';
    searchInput.value = '';
    const res = await fetch(`?action=get_images&folder=${folder}`);
    const images = await res.json();
    allImages = images;
    filteredImages = images;
    renderImages(filteredImages);
  }

  // ---------- RENDER IMAGES ----------
  function renderImages(images) {
    container.innerHTML = '';
    if (images.length===0) {
      const div = document.createElement('div');
      div.className = searchInput.value ? 'no-results' : 'add-btn-container';
      div.innerHTML = searchInput.value
        ? `<p>No images match "<strong>${searchInput.value}</strong>"</p>`
        : `<button id="add-first">+ Add Images (Bulk)</button>`;
      container.appendChild(div);
      if (!searchInput.value) div.querySelector('button').onclick = showBulkUpload;
      return;
    }
    const scroll = document.createElement('div');
    scroll.className = 'image-scroll';
    images.forEach((img,i)=>{
      const item = document.createElement('div');
      item.className = 'image-item';
      item.dataset.path = img.path;
      item.dataset.url = img.url;
      item.dataset.index = i;
      const ext = img.path.split('.').pop().toUpperCase();
      item.innerHTML = `
        <div class="checkbox"></div>
        <img src="${img.path}" alt="Image ${i+1}" loading="lazy">
        <p>#${i+1} • ${ext}</p>
      `;
      const cb = item.querySelector('.checkbox');
      cb.onclick = e=>{e.stopPropagation(); toggleSelect(item);};
      item.onclick = e=>{ if (e.target!==cb) openFullscreen(img.path, img.url); };
      scroll.appendChild(item);
    });
    container.appendChild(scroll);

    // Add Move to Uploaded Button (only for main folder)
    if (!currentFolder.endsWith('_uploaded')) {
      const moveBtn = document.createElement('div');
      moveBtn.style.textAlign = 'center';
      moveBtn.innerHTML = `<button class="move-to-uploaded-btn" id="move-to-uploaded-btn">Move to Uploaded</button>`;
      container.appendChild(moveBtn);
      moveBtn.querySelector('button').onclick = () => {
        moveUrls.placeholder = 'Paste image URLs, separated by commas';
        moveUrls.value = '';
        moveModal.style.display = 'flex';
      };
    }
    fab.style.display = 'flex';
    setupSelection();
  }

  // ---------- SEARCH (debounced) ----------
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const term = searchInput.value.trim().toLowerCase();
      if (!term) {
        filteredImages = allImages;
      } else {
        filteredImages = allImages.filter(img =>
          img.url.toLowerCase().includes(term) ||
          img.path.toLowerCase().includes(term)
        );
      }
      renderImages(filteredImages);
      // keep selection state consistent
      document.querySelectorAll('.image-item').forEach(item => {
        const path = item.dataset.path;
        if (selectedImages.has(path)) {
          item.classList.add('selected');
        } else {
          item.classList.remove('selected');
        }
      });
      updateSelectionUI();
    }, 250);
  });

  // ---------- SELECTION ----------
  function setupSelection() {
    selectionControls.style.display = 'flex';
    selectAllCheckbox.onchange = () => {
      const checked = selectAllCheckbox.checked;
      document.querySelectorAll('.image-item').forEach(item => {
        const path = item.dataset.path;
        if (checked) {
          selectedImages.add(path);
          item.classList.add('selected');
        } else {
          selectedImages.delete(path);
          item.classList.remove('selected');
        }
      });
      updateSelectionUI();
    };
    deleteSelectedBtn.onclick = showConfirmModal;
  }

  function toggleSelect(item) {
    const path = item.dataset.path;
    if (selectedImages.has(path)) {
      selectedImages.delete(path);
      item.classList.remove('selected');
    } else {
      selectedImages.add(path);
      item.classList.add('selected');
    }
    updateSelectionUI();
    const all = document.querySelectorAll('.image-item').length;
    const sel = selectedImages.size;
    selectAllCheckbox.checked = (all === sel && sel > 0);
  }

  function updateSelectionUI() {
    const cnt = selectedImages.size;
    selectedCountSpan.textContent = cnt;
    deleteSelectedBtn.style.display = cnt > 0 ? 'inline-block' : 'none';
  }

  // ---------- CONFIRM DELETE IMAGES ----------
  function showConfirmModal() {
    if (selectedImages.size===0) return;
    confirmCount.textContent = selectedImages.size;
    confirmModal.style.display = 'flex';
  }
  confirmNo.onclick = () => confirmModal.style.display = 'none';
  confirmYes.onclick = () => {
    confirmModal.style.display = 'none';
    const paths = Array.from(selectedImages);
    fetch('',{
      method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:`action=delete_images&folder=${currentFolder}&paths=${encodeURIComponent(JSON.stringify(paths))}`
    })
    .then(r=>r.json())
    .then(res=>{
      if (res.success) {
        selectedImages.clear();
        loadFolder(currentFolder, activeBtn.textContent);
      }
    });
  };

  // ---------- MOVE TO UPLOADED (by URL) ----------
  moveNo.onclick = () => { moveModal.style.display = 'none'; moveUrls.value = ''; };
  moveYes.onclick = () => {
    const raw = moveUrls.value.trim();
    if (!raw) return showAlert('Paste at least one image URL.');
    fetch('', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: `action=move_to_uploaded&folder=${currentFolder}&urls=${encodeURIComponent(raw)}`
    })
    .then(r => r.json())
    .then(res => {
      if (res.success) {
        moveModal.style.display = 'none';
        moveUrls.value = '';
        loadFolder(currentFolder, activeBtn.textContent);
      } else {
        showAlert(res.message || 'Move failed');
      }
    });
  };

  // ---------- BULK UPLOAD ----------
  fab.onclick = showBulkUpload;
  function showBulkUpload() {
    if (!currentFolder) return;
    document.getElementById('bulk-folder-name').textContent = activeBtn.textContent;
    document.getElementById('bulk-upload-overlay').style.display = 'flex';
    bulkFiles = [];
    updateBulkPreview();
  }
  const bulkOverlay = document.getElementById('bulk-upload-overlay');
  const bulkArea = document.getElementById('bulk-upload-area');
  const bulkInput = document.getElementById('bulk-input');
  const bulkChoose = document.getElementById('bulk-choose');
  const bulkCount = document.getElementById('bulk-count');
  const bulkPreview = document.getElementById('bulk-preview');
  const bulkProgress = document.getElementById('bulk-progress');
  const bulkFill = document.getElementById('bulk-fill');
  const bulkText = document.getElementById('bulk-text');
  const bulkSave = document.getElementById('bulk-save');
  const bulkCancel = document.getElementById('bulk-cancel');
  bulkChoose.onclick = () => bulkInput.click();
  bulkInput.onchange = () => handleBulkFiles(bulkInput.files);
  ['dragenter','dragover'].forEach(e=>bulkArea.addEventListener(e,()=>bulkArea.classList.add('dragover')));
  ['dragleave','drop'].forEach(e=>bulkArea.addEventListener(e,()=>bulkArea.classList.remove('dragover')));
  bulkArea.ondrop = e=>{e.preventDefault(); handleBulkFiles(e.dataTransfer.files);};
  function handleBulkFiles(files){
    const valid = Array.from(files).filter(f=>f.type.startsWith('image/'));
    bulkFiles = [...bulkFiles, ...valid];
    updateBulkPreview();
  }
  function updateBulkPreview(){
    bulkCount.textContent = `${bulkFiles.length} image(s) selected`;
    bulkPreview.innerHTML = '';
    bulkFiles.forEach((file,i)=>{
      const reader = new FileReader();
      reader.onload = e=>{
        const div = document.createElement('div');
        div.className='bulk-preview-item';
        div.innerHTML = `<img src="${e.target.result}" alt="Preview"><div class="bulk-remove" onclick="removeBulk(${i})">X</div>`;
        bulkPreview.appendChild(div);
      };
      reader.readAsDataURL(file);
    });
    bulkSave.style.display = bulkFiles.length>0 ? 'inline-block' : 'none';
  }
  window.removeBulk = i=>{ bulkFiles.splice(i,1); updateBulkPreview(); };
  bulkSave.onclick = ()=>{ if(bulkFiles.length) uploadBulkInChunks(); };
  bulkCancel.onclick = ()=>{ bulkOverlay.style.display='none'; bulkFiles=[]; };
  async function uploadBulkInChunks(){
    const chunkSize = 10;
    let uploaded = 0;
    bulkProgress.style.display='block';
    for(let i=0;i<bulkFiles.length;i+=chunkSize){
      const chunk = bulkFiles.slice(i,i+chunkSize);
      const form = new FormData();
      form.append('action','upload_images');
      form.append('folder',currentFolder);
      chunk.forEach(f=>form.append('images[]',f));
      await fetch('',{method:'POST',body:form})
        .then(r=>r.json())
        .then(res=>{
          uploaded += res.uploaded?.length||0;
          const pct = (uploaded/bulkFiles.length)*100;
          bulkFill.style.width = pct+'%';
          bulkText.textContent = `Uploaded ${uploaded} of ${bulkFiles.length}`;
        });
    }
    setTimeout(()=>{ bulkOverlay.style.display='none'; loadFolder(currentFolder, activeBtn.textContent); },600);
  }

  // ---------- FULLSCREEN ----------
  const fullscreenModal = document.getElementById('fullscreen-modal');
  const fullscreenImg = document.getElementById('fullscreen-img');
  const copyBtn = document.getElementById('copy-link-btn');
  const closeBtn = document.getElementById('close-fullscreen');
  const notif = document.getElementById('copied-notif');
  let currentImageUrl = '';
  function openFullscreen(path,url){
    fullscreenImg.src = path;
    currentImageUrl = url;
    fullscreenModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
  closeBtn  .onclick = ()=>{ fullscreenModal.style.display='none'; document.body.style.overflow='auto'; };
  copyBtn.onclick = ()=>{
    navigator.clipboard.writeText(currentImageUrl).then(()=>{
      notif.classList.add('show');
      setTimeout(()=>notif.classList.remove('show'),2000);
    });
  };

  // ESC close all modals
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){
      if(fullscreenModal.style.display==='flex') closeBtn.click();
      if(bulkOverlay.style.display==='flex') bulkCancel.click();
      if(confirmModal.style.display==='flex') confirmNo.click();
      if(renameModal.style.display==='flex') renameNo.click();
      if(deleteFolderModal.style.display==='flex') deleteFolderNo.click();
      if(moveModal.style.display==='flex') moveNo.click();
      if(alertModal.style.display==='flex') alertOk.click();
      if(folderMenu.classList.contains('show')) folderMenu.classList.remove('show');
    }
  });

  // Auto-load first folder
  if(folders.length>0) {
    loadFolder(folders[0].folder, folders[0].name);
  } else {
    activeBtn.textContent = 'No folders yet';
  }
  function formatName(str){return str.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());}
</script>
</body>
</html>