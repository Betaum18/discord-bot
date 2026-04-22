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

  } else if (data.aba == "Compras") {
    var wsComp = ss.getSheetByName("Compras") || ss.insertSheet("Compras");
    if (wsComp.getLastRow() == 0) wsComp.appendRow(["Comprador", "Família", "Item", "Quantidade", "Valor", "Observação", "Registrado em"]);
    wsComp.appendRow([data.comprador, data.familia, data.item, data.quantidade, data.valor, data.observacao, data.registrado_em]);

  } else if (data.aba == "LerCompras") {
    var wsComp2 = ss.getSheetByName("Compras");
    if (!wsComp2 || wsComp2.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var rowsComp = wsComp2.getRange(2, 1, wsComp2.getLastRow() - 1, 7).getValues();
    var listaComp = [];
    for (var i = 0; i < rowsComp.length; i++) {
      var r = rowsComp[i];
      if (r[0] == "") continue;
      if (data.comprador && data.comprador != "" && r[0] != data.comprador) continue;
      listaComp.push({
        comprador:    r[0],
        familia:      r[1],
        item:         r[2],
        quantidade:   r[3],
        valor:        r[4],
        observacao:   r[5],
        registrado_em: r[6]
      });
    }
    return ContentService.createTextOutput(JSON.stringify(listaComp)).setMimeType(ContentService.MimeType.JSON);

  // ── VENDA DE MUNIÇÃO (novo formato multi-tipo) ─────────────────────────────
  } else if (data.aba == "VendaMunicao") {
    var wsMun = ss.getSheetByName("VendaMunicao") || ss.insertSheet("VendaMunicao");
    if (wsMun.getLastRow() == 0) wsMun.appendRow(["Comprador", "Tipo Comprador", "Pistola", "Sub", "Fuzil", "Pagamento", "% Sujo", "Desconto (%)", "Preço Final", "Vendedor", "Registrado em"]);
    wsMun.appendRow([data.nome_comprador, data.tipo_comprador, data.pistola || 0, data.sub || 0, data.fuzil || 0, data.pagamento, data.percentual_sujo, data.desconto, data.preco_final, data.vendedor, data.registrado_em]);

  } else if (data.aba == "LerVendaMunicao") {
    var wsMun2 = ss.getSheetByName("VendaMunicao");
    if (!wsMun2 || wsMun2.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var rowsMun = wsMun2.getRange(2, 1, wsMun2.getLastRow() - 1, 11).getValues();
    var listaMun = [];
    for (var i = 0; i < rowsMun.length; i++) {
      var r = rowsMun[i];
      if (r[0] == "") continue;
      if (data.comprador && data.comprador != "" && r[0].toString().toLowerCase().indexOf(data.comprador.toLowerCase()) == -1) continue;
      listaMun.push({
        nome_comprador:  r[0],
        tipo_comprador:  r[1],
        pistola:         r[2],
        sub:             r[3],
        fuzil:           r[4],
        pagamento:       r[5],
        percentual_sujo: r[6],
        desconto:        r[7],
        preco_final:     r[8],
        vendedor:        r[9],
        registrado_em:   r[10]
      });
    }
    return ContentService.createTextOutput(JSON.stringify(listaMun)).setMimeType(ContentService.MimeType.JSON);

  // ── PREÇOS ─────────────────────────────────────────────────────────────────
  } else if (data.aba == "LerPrecos") {
    var wsPrecos = ss.getSheetByName("Precos");
    if (!wsPrecos || wsPrecos.getLastRow() <= 1) {
      return ContentService.createTextOutput("{}").setMimeType(ContentService.MimeType.JSON);
    }
    var rowsPrecos = wsPrecos.getRange(2, 1, wsPrecos.getLastRow() - 1, 2).getValues();
    var precos = {};
    for (var i = 0; i < rowsPrecos.length; i++) {
      if (rowsPrecos[i][0] != "") precos[rowsPrecos[i][0]] = rowsPrecos[i][1];
    }
    return ContentService.createTextOutput(JSON.stringify(precos)).setMimeType(ContentService.MimeType.JSON);

  } else if (data.aba == "AtualizarPreco") {
    var wsPrecos2 = ss.getSheetByName("Precos") || ss.insertSheet("Precos");
    if (wsPrecos2.getLastRow() == 0) wsPrecos2.appendRow(["Tipo", "Preco"]);
    var rowsP = wsPrecos2.getLastRow() > 1 ? wsPrecos2.getRange(2, 1, wsPrecos2.getLastRow() - 1, 2).getValues() : [];
    var foundP = false;
    for (var i = 0; i < rowsP.length; i++) {
      if (rowsP[i][0] == data.tipo) {
        wsPrecos2.getRange(i + 2, 2).setValue(data.preco);
        foundP = true;
        break;
      }
    }
    if (!foundP) wsPrecos2.appendRow([data.tipo, data.preco]);

  // ── ENCOMENDAS ─────────────────────────────────────────────────────────────
  } else if (data.aba == "CriarEncomenda") {
    var wsEnc = ss.getSheetByName("Encomendas") || ss.insertSheet("Encomendas");
    if (wsEnc.getLastRow() == 0) wsEnc.appendRow(["ID", "Vendedor", "Comprador", "Tipo Comprador", "Pistola Total", "Sub Total", "Fuzil Total", "Total (R$)", "Pistola Entregue", "Sub Entregue", "Fuzil Entregue", "Status", "Registrado em"]);
    var newId = String(Date.now());
    wsEnc.appendRow([newId, data.vendedor, data.comprador, data.tipo_comprador, data.pistola || 0, data.sub || 0, data.fuzil || 0, data.total, 0, 0, 0, "Pendente", data.registrado_em]);

  } else if (data.aba == "LerEncomendas") {
    var wsEnc2 = ss.getSheetByName("Encomendas");
    if (!wsEnc2 || wsEnc2.getLastRow() <= 1) {
      return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
    }
    var rowsEnc = wsEnc2.getRange(2, 1, wsEnc2.getLastRow() - 1, 13).getValues();
    var listaEnc = [];
    var filtro = data.status || "";
    for (var i = 0; i < rowsEnc.length; i++) {
      var r = rowsEnc[i];
      if (r[0] == "") continue;
      var st = r[11];
      if (filtro == "abertas" && st == "Completa") continue;
      if (filtro != "" && filtro != "abertas" && filtro != "todas" && st != filtro) continue;
      listaEnc.push({
        id:               String(r[0]),
        vendedor:         r[1],
        comprador:        r[2],
        tipo_comprador:   r[3],
        pistola_total:    r[4],
        sub_total:        r[5],
        fuzil_total:      r[6],
        total:            r[7],
        pistola_entregue: r[8],
        sub_entregue:     r[9],
        fuzil_entregue:   r[10],
        status:           st,
        registrado_em:    r[12]
      });
    }
    return ContentService.createTextOutput(JSON.stringify(listaEnc)).setMimeType(ContentService.MimeType.JSON);

  } else if (data.aba == "RegistrarEntrega") {
    var wsEnc3 = ss.getSheetByName("Encomendas");
    if (!wsEnc3) {
      return ContentService.createTextOutput('{"status":"Erro: planilha não encontrada"}').setMimeType(ContentService.MimeType.JSON);
    }
    var rowsEnc3 = wsEnc3.getLastRow() > 1 ? wsEnc3.getRange(2, 1, wsEnc3.getLastRow() - 1, 13).getValues() : [];
    for (var i = 0; i < rowsEnc3.length; i++) {
      if (String(rowsEnc3[i][0]) == String(data.id)) {
        var rowNum = i + 2;
        var pistTotal  = Number(rowsEnc3[i][4]);
        var subTotal   = Number(rowsEnc3[i][5]);
        var fuzilTotal = Number(rowsEnc3[i][6]);
        var pistEnt    = Math.min(Number(rowsEnc3[i][8])  + Number(data.pistola || 0), pistTotal);
        var subEnt     = Math.min(Number(rowsEnc3[i][9])  + Number(data.sub     || 0), subTotal);
        var fuzilEnt   = Math.min(Number(rowsEnc3[i][10]) + Number(data.fuzil   || 0), fuzilTotal);
        wsEnc3.getRange(rowNum, 9, 1, 3).setValues([[pistEnt, subEnt, fuzilEnt]]);
        var completo = (pistEnt >= pistTotal) && (subEnt >= subTotal) && (fuzilEnt >= fuzilTotal);
        var algumEntregue = pistEnt > 0 || subEnt > 0 || fuzilEnt > 0;
        var newStatus = completo ? "Completa" : (algumEntregue ? "Parcial" : "Pendente");
        wsEnc3.getRange(rowNum, 12).setValue(newStatus);
        return ContentService.createTextOutput(JSON.stringify({status: newStatus})).setMimeType(ContentService.MimeType.JSON);
      }
    }
    return ContentService.createTextOutput('{"status":"Erro: encomenda não encontrada"}').setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput('{"ok":true}').setMimeType(ContentService.MimeType.JSON);
}
