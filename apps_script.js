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
  }

  return ContentService.createTextOutput('{"ok":true}').setMimeType(ContentService.MimeType.JSON);
}
