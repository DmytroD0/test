function dtime(daysBefore) {
  var d = new Date(new Date() - 24 * 3600 * 1000 * daysBefore);
  d.setFullYear(d.getFullYear());
  var mnth = new Array(
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
    "10",
    "11",
    "12"
  );
  var month = new Array(
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre"
  );
  document.write(
    d.getDate() + " " + month[d.getMonth()] + " " + d.getFullYear()
  );
}

