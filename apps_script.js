function doGet(e) {
  var data = JSON.parse(e.parameter.data);
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  if (data.aba == "Vendedores") {
    var ws = ss.getSheetByName("Vendedores") || ss.insertSheet("Vendedores");
    if (ws.getLastRow() == 0) ws.appendRow(["Nome", "Data de Cadastro"]);
    ws.appendRow([data.nome, data.data]);

  } else if (data.aba == "Vendas") {
    var ws2 = ss.getSheetByName("Vendas") || ss.insertSheet("Vendas");
    if (ws2.getLastRow() == 0) ws2.appendRow(["Nome", "Data", "Item", "Quantidade", "Total", "Vendedor", "Registrado em"]);
    ws2.appendRow([data.nome, data.data, data.item, data.quantidade, data.total, data.vendedor, data.registrado_em]);

  } else if (data.aba == "LerVendedores") {
    var ws3 = ss.getSheetByName("Vendedores");
    if (!ws3 || ws3.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var valores = ws3.getRange(2, 1, ws3.getLastRow() - 1, 1).getValues();
    var lista = [];
    for (var i = 0; i < valores.length; i++) {
      if (valores[i][0] != "") lista.push(valores[i][0]);
    }
    return ContentService.createTextOutput(JSON.stringify(lista)).setMimeType(ContentService.MimeType.JSON);

  } else if (data.aba == "RemoverVendedor") {
    var ws4 = ss.getSheetByName("Vendedores");
    if (ws4) {
      var rows = ws4.getDataRange().getValues();
      for (var i = 1; i < rows.length; i++) {
        if (rows[i][0] == data.nome) {
          ws4.deleteRow(i + 1);
          break;
        }
      }
    }

  } else if (data.aba == "LerCraftItens") {
    var wsCraft = ss.getSheetByName("Crafts");
    if (!wsCraft || wsCraft.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var dados = wsCraft.getRange(2, 1, wsCraft.getLastRow() - 1, 1).getValues();
    var itens = [];
    for (var i = 0; i < dados.length; i++) {
      var nome = dados[i][0].toString().trim();
      if (nome != "" && itens.indexOf(nome) == -1) itens.push(nome);
    }
    return ContentService.createTextOutput(JSON.stringify(itens)).setMimeType(ContentService.MimeType.JSON);

  } else if (data.aba == "LerCraft") {
    var wsCraft2 = ss.getSheetByName("Crafts");
    if (!wsCraft2 || wsCraft2.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var todos = wsCraft2.getRange(2, 1, wsCraft2.getLastRow() - 1, 3).getValues();
    var materiais = [];
    for (var i = 0; i < todos.length; i++) {
      if (todos[i][0].toString().trim().toLowerCase() == data.item.toLowerCase()) {
        materiais.push({ material: todos[i][1], quantidade: todos[i][2] });
      }
    }
    return ContentService.createTextOutput(JSON.stringify(materiais)).setMimeType(ContentService.MimeType.JSON);

  } else if (data.aba == "EditarVendedor") {
    var ws5 = ss.getSheetByName("Vendedores");
    if (ws5) {
      var rows2 = ws5.getDataRange().getValues();
      for (var i = 1; i < rows2.length; i++) {
        if (rows2[i][0] == data.nome_atual) {
          ws5.getRange(i + 1, 1).setValue(data.nome_novo);
          break;
        }
      }
    }

  } else if (data.aba == "CadastrarAniversario") {
    var wsAniv = ss.getSheetByName("Aniversarios") || ss.insertSheet("Aniversarios");
    if (wsAniv.getLastRow() == 0) wsAniv.appendRow(["Nome", "Discord_ID", "Data"]);
    var rowsAniv = wsAniv.getLastRow() > 1 ? wsAniv.getRange(2, 1, wsAniv.getLastRow() - 1, 3).getValues() : [];
    var found = false;
    for (var i = 0; i < rowsAniv.length; i++) {
      if (String(rowsAniv[i][1]) == String(data.discord_id)) {
        wsAniv.getRange(i + 2, 1, 1, 3).setValues([[data.nome, data.discord_id, data.data]]);
        found = true;
        break;
      }
    }
    if (!found) wsAniv.appendRow([data.nome, data.discord_id, data.data]);

  } else if (data.aba == "LerAniversarios") {
    var wsAniv2 = ss.getSheetByName("Aniversarios");
    if (!wsAniv2 || wsAniv2.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var valoresAniv = wsAniv2.getRange(2, 1, wsAniv2.getLastRow() - 1, 3).getValues();
    var listaAniv = [];
    for (var i = 0; i < valoresAniv.length; i++) {
      if (valoresAniv[i][0] != "") {
        listaAniv.push({nome: valoresAniv[i][0], discord_id: String(valoresAniv[i][1]), data: valoresAniv[i][2]});
      }
    }
    return ContentService.createTextOutput(JSON.stringify(listaAniv)).setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput('{"ok":true}').setMimeType(ContentService.MimeType.JSON);
}
