/* Robotix MultiCharge native Home Assistant card: one backend, five honest views. */
let mcLanguage="en";
const MC_TEXT={"nl":{"Overview":"Overzicht","Charging Plan":"Laadplan","Chargeable Assets":"Voertuigen","Chargers":"Laadpalen","Settings":"Instellingen","Charging plan":"Laadplan","Charging overview":"Laadoverzicht","Refresh":"Vernieuwen","Today":"Vandaag","Tomorrow":"Morgen","All chargers":"Alle laadpalen","Show labels":"Toon","Color by":"Kleur per","Indicative forecasting":"Prognose","Vehicle":"Voertuig","Charger":"Laadpaal","Vehicle + Charger":"Voertuig + laadpaal","Show (not reserved)":"Tonen","Hide":"Verbergen","Proposed":"Voorgesteld","Accepted":"Bevestigd","Measured":"Gemeten","Indicative":"Indicatief","No vehicle selected":"Geen voertuig","Connected":"Aangesloten","Disconnected":"Niet aangesloten","Connection unknown":"Aansluiting onbekend","Vehicle unknown":"Voertuig onbekend","Unavailable":"Niet beschikbaar","Unknown":"Onbekend","Not set":"Niet ingesteld","Not assigned":"Niet toegewezen","Plan color":"Plankleur","Plan labels":"Planlabels","Active chargers":"Actieve laadpalen","Actual power":"Werkelijk vermogen","Current price":"Huidig tarief","Charging strategy":"Laadmodus","Charging site":"Laadlocatie","Solar production":"Zonneproductie","Home consumption":"Woningverbruik","Grid power":"Netvermogen","Solar surplus":"Zonne-overschot","Future tariff intervals":"Toekomstige tariefintervallen","Current import price":"Huidig aankoopttarief","Current export price":"Huidige injectievergoeding","Solar intervals":"Zonintervallen","Available surplus":"Beschikbaar overschot","Solar source":"Zonnebron","Grid direction":"Netrichting","Sources & bindings":"Bronnen","Safety & limits":"Veiligheid en limieten","Integrations":"Integraties","Readiness":"Gereedheid","Battery":"Batterij","Target":"Doel","Ready By":"Klaar om","Priority":"Prioriteit","Duration":"Duur","Requested energy":"Gevraagde energie","Charging intention":"Laadbehoefte","Charging priority":"Prioriteit","Connection":"Aansluiting","Selected vehicle":"Gekozen voertuig","Assigned asset":"Gekozen voertuig","Actual current":"Gemeten stroom","Power":"Vermogen","Source state":"Bronstatus","Status":"Status","Start charging":"Start laden","Stop charging":"Stop laden","Details":"Details","Hide details":"Sluiten","Edit":"Wijzigen","Saved":"Opgeslagen","Pending":"In behandeling","Rejected":"Geweigerd","Next planned session":"Volgende laadsessie","Next action":"Volgende stap","No active qualified vehicle plan":"Geen actieve planning","No qualified slots for this day.":"Geen laadmomenten","No vehicles":"Geen voertuigen","No charging points":"Geen laadpalen","Loading":"Laden","Error":"Fout","No data":"Geen gegevens","No connection":"Niet aangesloten","Not ready":"Niet gereed","Waiting":"Wachten","Forecast":"Prognose","If connected now":"Bij nu aansluiten","Expected":"Verwacht","Not reserved":"Niet gereserveerd","Measured power unavailable":"Geen meetgegevens","Vehicle plan":"Voertuigplan","Charger plan":"Laadpaalplan","No forecast":"Geen prognose","No vehicle":"Geen voertuig","Tariff":"Tarief","Proposed · pale color":"Voorgesteld","Accepted · solid color":"Geaccepteerd","Measured · physical source":"Gemeten","Indicative · dashed outline":"Indicatief","Add asset":"Voertuig toevoegen","Add charger":"Laadpaal toevoegen","Charging mode":"Laadmodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blauw","orange":"Oranje","green":"Groen","purple":"Paars","gold":"Goud","teal":"Blauwgroen","pink":"Roze","indigo":"Indigo","olive":"Olijfgroen","brown":"Bruin","coral":"Koraal","slate":"Leigrijs","violet":"Violet","lime":"Limoen","salmon":"Zalm","cyan":"Cyaan","wine":"Wijnrood","forest":"Bosgroen","peach":"Perzik","lavender":"Lavendel","turquoise":"Turkoois","rust":"Roest","navy":"Marineblauw","moss":"Mosgroen","Guest expired":"Gast verlopen","Ready":"Gereed","No tariff":"Geen tarief","No solar":"Geen zon","No deadline":"Geen eindtijd","No charging goal":"Geen laaddoel","Limited power":"Beperkt vermogen","No source":"Geen bron","No capacity":"Geen capaciteit","Wiring unknown":"Aansluiting onbekend","Guest":"Gast","Charged":"Geladen","Charging":"Laden","Stopped":"Gestopt","Confirmed":"Bevestigd","No action":"Geen actie","Reason":"Reden","Energy":"Energie","Repeat":"Herhalen","Measured session energy":"Sessie-energie","Last confirmed session":"Laatste sessie","Measured energy":"Gemeten energie","Verified cost":"Kosten","Current range":"Stroomsterkte","Measured confirmation":"Gemeten om","Control type":"Sturing","On/off":"Aan/uit","Variable current":"Variabele stroom","Unverified":"Onbekend","No charger assigned":"Geen laadpaal","Target battery %":"Doelbatterij %","Asset name":"Voertuignaam","Asset type":"Soort","Temporary guest":"Tijdelijke gast","Guest until":"Gast tot","Expected connection":"Verwachte aansluiting","Save charging site":"Laadlocatie opslaan","Save sources":"Bronnen opslaan","Maximum group kW":"Max. vermogen kW","Group power ceiling kW":"Max. vermogen kW","Site name":"Locatienaam","Parallel chargers":"Gelijktijdige laders","Save electrical limits":"Limieten opslaan","Electrical limits":"Limieten","Battery data":"Batterijbron","Rated power":"Nominaal vermogen","Phases":"Fasen","Active session":"Actieve sessie","Add a chargeable asset":"Voertuig toevoegen","Create asset":"Toevoegen","Cancel adding":"Annuleren","Remove":"Verwijderen","Effective charging power":"Effectief laadvermogen","Car":"Auto","Bicycle":"Fiets","Motorcycle":"Motorfiets","Scooter":"Scooter","Other":"Overig","No active plan":"Geen actieve planning","Confirm connected vehicle":"Bevestig aangesloten voertuig","Connected vehicle":"Aangesloten voertuig","Not confirmed":"Niet bevestigd"},"fr":{"Overview":"Vue d’ensemble","Charging Plan":"Plan de charge","Chargeable Assets":"Véhicules","Chargers":"Bornes","Settings":"Réglages","Charging plan":"Plan de charge","Charging overview":"Vue des charges","Refresh":"Actualiser","Today":"Aujourd’hui","Tomorrow":"Demain","All chargers":"Toutes les bornes","Show labels":"Afficher","Color by":"Couleur par","Indicative forecasting":"Prévision","Vehicle":"Véhicule","Charger":"Borne","Vehicle + Charger":"Véhicule + borne","Show (not reserved)":"Afficher","Hide":"Masquer","Proposed":"Proposé","Accepted":"Confirmé","Measured":"Mesuré","Indicative":"Indicatif","No vehicle selected":"Aucun véhicule","Connected":"Connecté","Disconnected":"Déconnecté","Connection unknown":"Connexion inconnue","Vehicle unknown":"Véhicule inconnu","Unavailable":"Indisponible","Unknown":"Inconnu","Not set":"Non défini","Not assigned":"Non attribué","Plan color":"Couleur du plan","Plan labels":"Libellés du plan","Active chargers":"Bornes actives","Actual power":"Puissance réelle","Current price":"Tarif actuel","Charging strategy":"Mode de charge","Charging site":"Site de recharge","Solar production":"Production solaire","Home consumption":"Consommation du logement","Grid power":"Puissance du réseau","Solar surplus":"Surplus solaire","Future tariff intervals":"Intervalles futurs de prix","Current import price":"Prix d'achat actuel","Current export price":"Prix de vente actuel","Solar intervals":"Intervalles solaires","Available surplus":"Surplus disponible","Solar source":"Source solaire","Grid direction":"Sens du réseau","Sources & bindings":"Sources","Safety & limits":"Sécurité et limites","Integrations":"Intégrations","Readiness":"Disponibilité","Battery":"Batterie","Target":"Cible","Ready By":"Prêt pour","Priority":"Priorité","Duration":"Durée","Requested energy":"Énergie demandée","Charging intention":"Besoin de charge","Charging priority":"Priorité","Connection":"Connexion","Selected vehicle":"Véhicule choisi","Assigned asset":"Véhicule choisi","Actual current":"Courant réel","Power":"Puissance","Source state":"État de la source","Status":"État","Start charging":"Démarrer","Stop charging":"Arrêter","Details":"Détails","Hide details":"Fermer","Edit":"Modifier","Saved":"Enregistré","Pending":"En attente","Rejected":"Refusé","Next planned session":"Prochaine charge","Next action":"Prochaine étape","No active qualified vehicle plan":"Aucune charge prévue","No qualified slots for this day.":"Aucun créneau","No vehicles":"Aucun véhicule","No charging points":"Aucune borne","Loading":"Chargement","Error":"Erreur","No data":"Aucune donnée","No connection":"Déconnecté","Not ready":"Non prêt","Waiting":"En attente","Forecast":"Prévision","If connected now":"Si connecté maintenant","Expected":"Prévu","Not reserved":"Non réservé","Measured power unavailable":"Mesure indisponible","Vehicle plan":"Plan véhicule","Charger plan":"Plan borne","No forecast":"Aucune prévision","No vehicle":"Aucun véhicule","Tariff":"Tarif","Proposed · pale color":"Proposé","Accepted · solid color":"Accepté","Measured · physical source":"Mesuré","Indicative · dashed outline":"Indicatif","Add asset":"Ajouter un véhicule","Add charger":"Ajouter borne","Charging mode":"Mode de charge","Mode":"Mode","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Bleu","orange":"Orange","green":"Vert","purple":"Violet","gold":"Or","teal":"Sarcelle","pink":"Rose","indigo":"Indigo","olive":"Olive","brown":"Marron","coral":"Corail","slate":"Ardoise","violet":"Mauve","lime":"Citron vert","salmon":"Saumon","cyan":"Cyan","wine":"Bordeaux","forest":"Vert forêt","peach":"Pêche","lavender":"Lavande","turquoise":"Turquoise","rust":"Rouille","navy":"Bleu marine","moss":"Vert mousse","Guest expired":"Invité expiré","Ready":"Prêt","No tariff":"Aucun tarif","No solar":"Pas de solaire","No deadline":"Pas d’échéance","No charging goal":"Aucune cible","Limited power":"Puissance limitée","No source":"Aucune source","No capacity":"Pas de capacité","Wiring unknown":"Câblage inconnu","Guest":"Invité","Charged":"Chargé","Charging":"Recharge","Stopped":"Arrêté","Confirmed":"Confirmé","No action":"Aucune action","Reason":"Motif","Energy":"Énergie","Repeat":"Répéter","Measured session energy":"Énergie de session","Last confirmed session":"Dernière session","Measured energy":"Énergie mesurée","Verified cost":"Coût","Current range":"Plage de courant","Measured confirmation":"Mesuré à","Control type":"Commande","On/off":"Marche/arrêt","Variable current":"Courant variable","Unverified":"Inconnu","No charger assigned":"Aucune borne","Target battery %":"Batterie cible %","Asset name":"Nom du véhicule","Asset type":"Type","Temporary guest":"Invité temporaire","Guest until":"Invité jusqu’à","Expected connection":"Connexion prévue","Save charging site":"Enregistrer le site","Save sources":"Enregistrer les sources","Maximum group kW":"Puissance max. kW","Group power ceiling kW":"Puissance max. kW","Site name":"Nom du site","Parallel chargers":"Bornes simultanées","Save electrical limits":"Enregistrer les limites","Electrical limits":"Limites","Battery data":"Source batterie","Rated power":"Puissance nominale","Phases":"Phases","Active session":"Session active","Add a chargeable asset":"Ajouter un véhicule","Create asset":"Ajouter","Cancel adding":"Annuler","Remove":"Supprimer","Effective charging power":"Puissance de charge effective","Car":"Voiture","Bicycle":"Vélo","Motorcycle":"Moto","Scooter":"Trottinette","Other":"Autre","No active plan":"Aucune charge planifiée","Confirm connected vehicle":"Confirmer le véhicule branché","Connected vehicle":"Véhicule branché","Not confirmed":"Non confirmé"},"da":{"Overview":"Overblik","Charging Plan":"Ladeplan","Chargeable Assets":"Køretøjer","Chargers":"Ladere","Settings":"Indstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversigt","Refresh":"Opdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farve efter","Indicative forecasting":"Prognose","Vehicle":"Køretøj","Charger":"Lader","Vehicle + Charger":"Køretøj + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslået","Accepted":"Accepteret","Measured":"Målt","Indicative":"Vejledende","No vehicle selected":"Intet køretøj valgt","Connected":"Tilsluttet","Disconnected":"Ikke tilsluttet","Connection unknown":"Tilslutning ukendt","Vehicle unknown":"Køretøj ukendt","Unavailable":"Ikke tilgængelig","Unknown":"Ukendt","Not set":"Ikke angivet","Not assigned":"Ikke tildelt","Plan color":"Planfarve","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Aktuel effekt","Current price":"Aktuel pris","Charging strategy":"Ladetilstand","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhed og grænser","Integrations":"Integrationer","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar kl.","Priority":"Prioritet","Duration":"Varighed","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilslutning","Selected vehicle":"Valgt køretøj","Assigned asset":"Tildelt køretøj","Actual current":"Aktuel strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start opladning","Stop charging":"Stop opladning","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Gemt","Pending":"Afventer","Rejected":"Afvist","Next planned session":"Næste planlagte opladning","Next action":"Næste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen køretøjer","No charging points":"Ingen ladere","Loading":"Indlæser","Error":"Fejl","No data":"Ingen data","No connection":"Ikke tilsluttet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilsluttet nu","Expected":"Forventet","Not reserved":"Ikke reserveret","Measured power unavailable":"Ingen måledata","Vehicle plan":"Køretøjsplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Intet køretøj","Tariff":"Tarif","Proposed · pale color":"Foreslået","Accepted · solid color":"Accepteret","Measured · physical source":"Målt","Indicative · dashed outline":"Vejledende","Add asset":"Tilføj køretøj","Add charger":"Tilføj lader","Charging mode":"Ladetilstand","Mode":"Tilstand","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grøn","purple":"Lilla","gold":"Guld","teal":"Blågrøn","pink":"Pink","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Koral","slate":"Skifer","violet":"Violet","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skovgrøn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosgrøn","Guest expired":"Gæst udløbet","Ready":"Klar","No tariff":"Ingen tarif","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Intet lademål","Limited power":"Begrænset effekt","No source":"Ingen kilde","No capacity":"Ingen kapacitet","Wiring unknown":"Ukendt ledningsføring","Guest":"Gæst","Charged":"Opladet","Charging":"Oplader","Stopped":"Stoppet","Confirmed":"Bekræftet","No action":"Ingen handling","Reason":"Årsag","Energy":"Energi","Repeat":"Gentag","Measured session energy":"Målt sessionsenergi","Last confirmed session":"Sidste session","Measured energy":"Målt energi","Verified cost":"Bekræftet pris","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Til/fra","Variable current":"Variabel strøm","Unverified":"Ikke verificeret","No charger assigned":"Ingen lader valgt","Target battery %":"Målbatteri %","Asset name":"Køretøjsnavn","Asset type":"Køretøjstype","Temporary guest":"Midlertidig gæst","Guest until":"Gæst indtil","Expected connection":"Forventet tilslutning","Save charging site":"Gem ladested","Save sources":"Gem kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrænse kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Gem elektriske grænser","Electrical limits":"Elektriske grænser","Battery data":"Batterikilde","Rated power":"Nominel effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Tilføj køretøj","Create asset":"Opret køretøj","Cancel adding":"Annuller","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Scooter","Other":"Andet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekræft tilsluttet køretøj","Connected vehicle":"Tilsluttet køretøj","Not confirmed":"Ikke bekræftet"},"nb":{"Overview":"Oversikt","Charging Plan":"Ladeplan","Chargeable Assets":"Kjøretøy","Chargers":"Ladere","Settings":"Innstillinger","Charging plan":"Ladeplan","Charging overview":"Ladeoversikt","Refresh":"Oppdater","Today":"I dag","Tomorrow":"I morgen","All chargers":"Alle ladere","Show labels":"Vis etiketter","Color by":"Farge etter","Indicative forecasting":"Prognose","Vehicle":"Kjøretøy","Charger":"Lader","Vehicle + Charger":"Kjøretøy + lader","Show (not reserved)":"Vis","Hide":"Skjul","Proposed":"Foreslått","Accepted":"Godkjent","Measured":"Målt","Indicative":"Veiledende","No vehicle selected":"Ingen kjøretøy valgt","Connected":"Tilkoblet","Disconnected":"Ikke tilkoblet","Connection unknown":"Tilkobling ukjent","Vehicle unknown":"Kjøretøy ukjent","Unavailable":"Ikke tilgjengelig","Unknown":"Ukjent","Not set":"Ikke angitt","Not assigned":"Ikke tilordnet","Plan color":"Planfarge","Plan labels":"Planetiketter","Active chargers":"Aktive ladere","Actual power":"Faktisk effekt","Current price":"Gjeldende pris","Charging strategy":"Lademodus","Charging site":"Ladested","Sources & bindings":"Kilder","Safety & limits":"Sikkerhet og grenser","Integrations":"Integrasjoner","Readiness":"Klar","Battery":"Batteri","Target":"Mål","Ready By":"Klar innen","Priority":"Prioritet","Duration":"Varighet","Requested energy":"Ønsket energi","Charging intention":"Ladebehov","Charging priority":"Ladeprioritet","Connection":"Tilkobling","Selected vehicle":"Valgt kjøretøy","Assigned asset":"Tilordnet kjøretøy","Actual current":"Faktisk strøm","Power":"Effekt","Source state":"Kildestatus","Status":"Status","Start charging":"Start lading","Stop charging":"Stopp lading","Details":"Detaljer","Hide details":"Skjul detaljer","Edit":"Rediger","Saved":"Lagret","Pending":"Venter","Rejected":"Avvist","Next planned session":"Neste planlagte lading","Next action":"Neste handling","No active qualified vehicle plan":"Ingen aktiv ladeplan","No qualified slots for this day.":"Ingen ladetider","No vehicles":"Ingen kjøretøy","No charging points":"Ingen ladere","Loading":"Laster","Error":"Feil","No data":"Ingen data","No connection":"Ikke tilkoblet","Not ready":"Ikke klar","Waiting":"Venter","Forecast":"Prognose","If connected now":"Hvis tilkoblet nå","Expected":"Forventet","Not reserved":"Ikke reservert","Measured power unavailable":"Ingen måledata","Vehicle plan":"Kjøretøyplan","Charger plan":"Ladeplan","No forecast":"Ingen prognose","No vehicle":"Ingen kjøretøy","Tariff":"Pris","Proposed · pale color":"Foreslått","Accepted · solid color":"Godkjent","Measured · physical source":"Målt","Indicative · dashed outline":"Veiledende","Add asset":"Legg til kjøretøy","Add charger":"Legg til lader","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Oransje","green":"Grønn","purple":"Lilla","gold":"Gull","teal":"Blågrønn","pink":"Rosa","indigo":"Indigo","olive":"Oliven","brown":"Brun","coral":"Korall","slate":"Skifer","violet":"Fiolett","lime":"Lime","salmon":"Laks","cyan":"Cyan","wine":"Vinrød","forest":"Skoggrønn","peach":"Fersken","lavender":"Lavendel","turquoise":"Turkis","rust":"Rust","navy":"Marineblå","moss":"Mosegrønn","Guest expired":"Gjest utløpt","Ready":"Klar","No tariff":"Ingen pris","No solar":"Ingen sol","No deadline":"Ingen frist","No charging goal":"Ingen lademål","Limited power":"Begrenset effekt","No source":"Ingen kilde","No capacity":"Ingen kapasitet","Wiring unknown":"Ukjent kabling","Guest":"Gjest","Charged":"Ladet","Charging":"Lader","Stopped":"Stoppet","Confirmed":"Bekreftet","No action":"Ingen handling","Reason":"Årsak","Energy":"Energi","Repeat":"Gjenta","Measured session energy":"Målt øktenergi","Last confirmed session":"Siste økt","Measured energy":"Målt energi","Verified cost":"Bekreftet kostnad","Current range":"Strømområde","Measured confirmation":"Målt kl.","Control type":"Styringstype","On/off":"Av/på","Variable current":"Variabel strøm","Unverified":"Ikke verifisert","No charger assigned":"Ingen lader valgt","Target battery %":"Batterimål %","Asset name":"Kjøretøynavn","Asset type":"Kjøretøytype","Temporary guest":"Midlertidig gjest","Guest until":"Gjest til","Expected connection":"Forventet tilkobling","Save charging site":"Lagre ladested","Save sources":"Lagre kilder","Maximum group kW":"Maks. effekt kW","Group power ceiling kW":"Effektgrense kW","Site name":"Stedsnavn","Parallel chargers":"Samtidige ladere","Save electrical limits":"Lagre grenser","Electrical limits":"Elektriske grenser","Battery data":"Batterikilde","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv økt","Add a chargeable asset":"Legg til kjøretøy","Create asset":"Opprett kjøretøy","Cancel adding":"Avbryt","Remove":"Fjern","Effective charging power":"Effektiv ladeeffekt","Car":"Bil","Bicycle":"Sykkel","Motorcycle":"Motorsykkel","Scooter":"Sparkesykkel","Other":"Annet","No active plan":"Ingen aktiv ladeplan","Confirm connected vehicle":"Bekreft tilkoblet kjøretøy","Connected vehicle":"Tilkoblet kjøretøy","Not confirmed":"Ikke bekreftet"},"sv":{"Overview":"Översikt","Charging Plan":"Laddplan","Chargeable Assets":"Fordon","Chargers":"Laddare","Settings":"Inställningar","Charging plan":"Laddplan","Charging overview":"Laddöversikt","Refresh":"Uppdatera","Today":"I dag","Tomorrow":"I morgon","All chargers":"Alla laddare","Show labels":"Visa etiketter","Color by":"Färg efter","Indicative forecasting":"Prognos","Vehicle":"Fordon","Charger":"Laddare","Vehicle + Charger":"Fordon + laddare","Show (not reserved)":"Visa","Hide":"Dölj","Proposed":"Föreslaget","Accepted":"Godkänt","Measured":"Mätt","Indicative":"Preliminärt","No vehicle selected":"Inget fordon valt","Connected":"Ansluten","Disconnected":"Inte ansluten","Connection unknown":"Anslutning okänd","Vehicle unknown":"Fordon okänt","Unavailable":"Inte tillgänglig","Unknown":"Okänd","Not set":"Inte angiven","Not assigned":"Inte tilldelad","Plan color":"Planfärg","Plan labels":"Planetiketter","Active chargers":"Aktiva laddare","Actual power":"Faktisk effekt","Current price":"Aktuellt pris","Charging strategy":"Laddläge","Charging site":"Laddplats","Sources & bindings":"Källor","Safety & limits":"Säkerhet och gränser","Integrations":"Integrationer","Readiness":"Redo","Battery":"Batteri","Target":"Mål","Ready By":"Klar senast","Priority":"Prioritet","Duration":"Varaktighet","Requested energy":"Önskad energi","Charging intention":"Laddbehov","Charging priority":"Laddprioritet","Connection":"Anslutning","Selected vehicle":"Valt fordon","Assigned asset":"Tilldelat fordon","Actual current":"Faktisk ström","Power":"Effekt","Source state":"Källstatus","Status":"Status","Start charging":"Starta laddning","Stop charging":"Stoppa laddning","Details":"Detaljer","Hide details":"Dölj detaljer","Edit":"Ändra","Saved":"Sparat","Pending":"Väntar","Rejected":"Avvisat","Next planned session":"Nästa planerade laddning","Next action":"Nästa åtgärd","No active qualified vehicle plan":"Ingen aktiv laddplan","No qualified slots for this day.":"Inga laddtider","No vehicles":"Inga fordon","No charging points":"Inga laddare","Loading":"Läser in","Error":"Fel","No data":"Inga data","No connection":"Inte ansluten","Not ready":"Inte redo","Waiting":"Väntar","Forecast":"Prognos","If connected now":"Om ansluten nu","Expected":"Förväntad","Not reserved":"Inte reserverad","Measured power unavailable":"Inga mätdata","Vehicle plan":"Fordonsplan","Charger plan":"Laddplan","No forecast":"Ingen prognos","No vehicle":"Inget fordon","Tariff":"Pris","Proposed · pale color":"Föreslaget","Accepted · solid color":"Godkänt","Measured · physical source":"Mätt","Indicative · dashed outline":"Preliminärt","Add asset":"Lägg till fordon","Add charger":"Lägg till laddare","Charging mode":"Laddläge","Mode":"Läge","Plan":"Plan","Home Assistant":"Home Assistant","blue":"Blå","orange":"Orange","green":"Grön","purple":"Lila","gold":"Guld","teal":"Blågrön","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Brun","coral":"Korall","slate":"Skiffer","violet":"Violett","lime":"Lime","salmon":"Lax","cyan":"Cyan","wine":"Vinröd","forest":"Skogsgrön","peach":"Persika","lavender":"Lavendel","turquoise":"Turkos","rust":"Rost","navy":"Marinblå","moss":"Mossgrön","Guest expired":"Gäst utgången","Ready":"Redo","No tariff":"Inget pris","No solar":"Ingen sol","No deadline":"Ingen tidsgräns","No charging goal":"Inget laddmål","Limited power":"Begränsad effekt","No source":"Ingen källa","No capacity":"Ingen kapacitet","Wiring unknown":"Okänd ledning","Guest":"Gäst","Charged":"Laddad","Charging":"Laddar","Stopped":"Stoppad","Confirmed":"Bekräftad","No action":"Ingen åtgärd","Reason":"Orsak","Energy":"Energi","Repeat":"Upprepa","Measured session energy":"Uppmätt sessionsenergi","Last confirmed session":"Senaste session","Measured energy":"Uppmätt energi","Verified cost":"Bekräftad kostnad","Current range":"Strömområde","Measured confirmation":"Mätt kl.","Control type":"Styrningstyp","On/off":"På/av","Variable current":"Variabel ström","Unverified":"Inte verifierad","No charger assigned":"Ingen laddare vald","Target battery %":"Batterimål %","Asset name":"Fordonsnamn","Asset type":"Fordonstyp","Temporary guest":"Tillfällig gäst","Guest until":"Gäst till","Expected connection":"Förväntad anslutning","Save charging site":"Spara laddplats","Save sources":"Spara källor","Maximum group kW":"Max. effekt kW","Group power ceiling kW":"Effektgräns kW","Site name":"Platsnamn","Parallel chargers":"Samtidiga laddare","Save electrical limits":"Spara gränser","Electrical limits":"Elektriska gränser","Battery data":"Batterikälla","Rated power":"Nominell effekt","Phases":"Faser","Active session":"Aktiv session","Add a chargeable asset":"Lägg till fordon","Create asset":"Skapa fordon","Cancel adding":"Avbryt","Remove":"Ta bort","Effective charging power":"Effektiv laddeffekt","Car":"Bil","Bicycle":"Cykel","Motorcycle":"Motorcykel","Scooter":"Elsparkcykel","Other":"Annat","No active plan":"Ingen aktiv laddplan","Confirm connected vehicle":"Bekräfta anslutet fordon","Connected vehicle":"Anslutet fordon","Not confirmed":"Inte bekräftat"},"de":{"Overview":"Übersicht","Charging Plan":"Ladeplan","Chargeable Assets":"Lade-Assets","Chargers":"Ladepunkte","Settings":"Einstellungen","Charging plan":"Ladeplan","Charging overview":"Ladeübersicht","Refresh":"Aktualisieren","Today":"Heute","Tomorrow":"Morgen","All chargers":"Alle Ladepunkte","Show labels":"Beschriftung","Color by":"Farbe nach","Indicative forecasting":"Prognose","Vehicle":"Asset","Charger":"Ladepunkt","Vehicle + Charger":"Asset + Ladepunkt","Show (not reserved)":"Anzeigen","Hide":"Ausblenden","Proposed":"Vorgeschlagen","Accepted":"Angenommen","Measured":"Gemessen","Indicative":"Unverbindlich","No vehicle selected":"Kein Asset gewählt","Connected":"Verbunden","Disconnected":"Nicht verbunden","Connection unknown":"Verbindung unbekannt","Vehicle unknown":"Asset unbekannt","Unavailable":"Nicht verfügbar","Unknown":"Unbekannt","Not set":"Nicht festgelegt","Not assigned":"Nicht zugewiesen","Plan color":"Planfarbe","Plan labels":"Planbeschriftung","Active chargers":"Aktive Ladepunkte","Actual power":"Ist-Leistung","Current price":"Aktueller Preis","Charging strategy":"Lademodus","Charging site":"Ladestandort","Solar production":"Solarproduktion","Home consumption":"Hausverbrauch","Grid power":"Netzleistung","Solar surplus":"Solarüberschuss","Future tariff intervals":"Zukünftige Preisintervalle","Current import price":"Aktueller Bezugspreis","Current export price":"Aktueller Einspeisepreis","Solar intervals":"Solarintervalle","Available surplus":"Verfügbarer Überschuss","Solar source":"Solarquelle","Grid direction":"Netzrichtung","Sources & bindings":"Quellen und Zuordnung","Safety & limits":"Sicherheit und Grenzen","Integrations":"Integrationen","Readiness":"Bereitschaft","Battery":"Batterie","Target":"Ziel","Ready By":"Bereit bis","Priority":"Priorität","Duration":"Dauer","Requested energy":"Energiebedarf","Charging intention":"Ladebedarf","Charging priority":"Ladepriorität","Connection":"Verbindung","Selected vehicle":"Ausgewähltes Asset","Assigned asset":"Zugeordnetes Asset","Actual current":"Ist-Strom","Power":"Leistung","Source state":"Quellenstatus","Status":"Status","Start charging":"Laden starten","Stop charging":"Laden stoppen","Details":"Details","Hide details":"Details schließen","Edit":"Bearbeiten","Saved":"Gespeichert","Pending":"Ausstehend","Rejected":"Abgelehnt","Next planned session":"Nächste Ladesitzung","Next action":"Nächste Aktion","No active qualified vehicle plan":"Kein aktiver Ladeplan","No qualified slots for this day.":"Keine Ladezeiten","No vehicles":"Keine Assets","No charging points":"Keine Ladepunkte","Loading":"Lädt","Error":"Fehler","No data":"Keine Daten","No connection":"Nicht verbunden","Not ready":"Nicht bereit","Waiting":"Warten","Forecast":"Prognose","If connected now":"Falls jetzt verbunden","Expected":"Erwartet","Not reserved":"Nicht reserviert","Measured power unavailable":"Keine Messdaten","Vehicle plan":"Assetplan","Charger plan":"Ladepunktplan","No forecast":"Keine Prognose","No vehicle":"Kein Asset","Tariff":"Tarif","Proposed · pale color":"Vorgeschlagen","Accepted · solid color":"Angenommen","Measured · physical source":"Gemessen","Indicative · dashed outline":"Unverbindlich","Add asset":"Asset hinzufügen","Add charger":"Ladepunkt hinzufügen","Charging mode":"Lademodus","Mode":"Modus","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Gast abgelaufen","Ready":"Bereit","No tariff":"Kein Tarif","No solar":"Kein Solar","No deadline":"Keine Frist","No charging goal":"Kein Ladeziel","Limited power":"Begrenzte Leistung","No source":"Keine Quelle","No capacity":"Keine Kapazität","Wiring unknown":"Verdrahtung unbekannt","Guest":"Gast","Charged":"Geladen","Charging":"Lädt","Stopped":"Gestoppt","Confirmed":"Bestätigt","No action":"Keine Aktion","Reason":"Grund","Energy":"Energie","Repeat":"Wiederholen","Measured session energy":"Gemessene Sitzungsenergie","Last confirmed session":"Letzte bestätigte Sitzung","Measured energy":"Gemessene Energie","Verified cost":"Verifizierte Kosten","Current range":"Strombereich","Measured confirmation":"Messzeit","Control type":"Steuerungstyp","On/off":"Ein/Aus","Variable current":"Variabler Strom","Unverified":"Nicht verifiziert","No charger assigned":"Kein Ladepunkt zugewiesen","Target battery %":"Batterieziel %","Asset name":"Assetname","Asset type":"Assettyp","Temporary guest":"Temporärer Gast","Guest until":"Gast bis","Expected connection":"Erwartete Verbindung","Save charging site":"Ladestandort speichern","Save sources":"Quellen speichern","Maximum group kW":"Maximale Gruppenleistung kW","Group power ceiling kW":"Gruppenleistungsgrenze kW","Site name":"Standortname","Parallel chargers":"Gleichzeitige Ladepunkte","Save electrical limits":"Elektrische Grenzen speichern","Electrical limits":"Elektrische Grenzen","Battery data":"Batteriedaten","Rated power":"Nennleistung","Phases":"Phasen","Active session":"Aktive Sitzung","Add a chargeable asset":"Lade-Asset hinzufügen","Create asset":"Asset erstellen","Cancel adding":"Abbrechen","Remove":"Entfernen","blue":"Blau","orange":"Orange","green":"Grün","purple":"Lila","gold":"Gold","teal":"Blaugrün","pink":"Rosa","indigo":"Indigo","olive":"Oliv","brown":"Braun","coral":"Koralle","slate":"Schiefer","violet":"Violett","lime":"Limette","salmon":"Lachs","cyan":"Cyan","wine":"Weinrot","forest":"Waldgrün","peach":"Pfirsich","lavender":"Lavendel","turquoise":"Türkis","rust":"Rost","navy":"Marineblau","moss":"Moosgrün","Effective charging power":"Effektive Ladeleistung","Car":"Auto","Bicycle":"Fahrrad","Motorcycle":"Motorrad","Scooter":"Roller","Other":"Sonstiges","No active plan":"Kein aktiver Ladeplan","Confirm connected vehicle":"Angeschlossenes Fahrzeug bestätigen","Connected vehicle":"Angeschlossenes Fahrzeug","Not confirmed":"Nicht bestätigt"},"es":{"Overview":"Resumen","Charging Plan":"Plan de carga","Chargeable Assets":"Activos de carga","Chargers":"Puntos de carga","Settings":"Ajustes","Charging plan":"Plan de carga","Charging overview":"Resumen de carga","Refresh":"Actualizar","Today":"Hoy","Tomorrow":"Mañana","All chargers":"Todos los puntos","Show labels":"Mostrar etiquetas","Color by":"Color por","Indicative forecasting":"Previsión","Vehicle":"Activo","Charger":"Punto de carga","Vehicle + Charger":"Activo + punto","Show (not reserved)":"Mostrar","Hide":"Ocultar","Proposed":"Propuesto","Accepted":"Aceptado","Measured":"Medido","Indicative":"Indicativo","No vehicle selected":"Ningún activo seleccionado","Connected":"Conectado","Disconnected":"Desconectado","Connection unknown":"Conexión desconocida","Vehicle unknown":"Activo desconocido","Unavailable":"No disponible","Unknown":"Desconocido","Not set":"Sin definir","Not assigned":"Sin asignar","Plan color":"Color del plan","Plan labels":"Etiquetas del plan","Active chargers":"Puntos activos","Actual power":"Potencia real","Current price":"Precio actual","Charging strategy":"Modo de carga","Charging site":"Instalación de carga","Sources & bindings":"Fuentes y asignación","Safety & limits":"Seguridad y límites","Integrations":"Integraciones","Readiness":"Preparación","Battery":"Batería","Target":"Objetivo","Ready By":"Listo para","Priority":"Prioridad","Duration":"Duración","Requested energy":"Energía solicitada","Charging intention":"Necesidad de carga","Charging priority":"Prioridad de carga","Connection":"Conexión","Selected vehicle":"Activo seleccionado","Assigned asset":"Activo asignado","Actual current":"Corriente real","Power":"Potencia","Source state":"Estado de fuente","Status":"Estado","Start charging":"Iniciar carga","Stop charging":"Detener carga","Details":"Detalles","Hide details":"Cerrar detalles","Edit":"Editar","Saved":"Guardado","Pending":"Pendiente","Rejected":"Rechazado","Next planned session":"Próxima carga","Next action":"Siguiente acción","No active qualified vehicle plan":"Sin plan activo","No qualified slots for this day.":"Sin franjas de carga","No vehicles":"Sin activos","No charging points":"Sin puntos de carga","Loading":"Cargando","Error":"Error","No data":"Sin datos","No connection":"Sin conexión","Not ready":"No preparado","Waiting":"Esperando","Forecast":"Previsión","If connected now":"Si se conecta ahora","Expected":"Previsto","Not reserved":"No reservado","Measured power unavailable":"Sin datos medidos","Vehicle plan":"Plan por activo","Charger plan":"Plan por punto","No forecast":"Sin previsión","No vehicle":"Sin activo","Tariff":"Tarifa","Proposed · pale color":"Propuesto","Accepted · solid color":"Aceptado","Measured · physical source":"Medido","Indicative · dashed outline":"Indicativo","Add asset":"Añadir activo","Add charger":"Añadir punto","Charging mode":"Modo de carga","Mode":"Modo","Plan":"Plan","Home Assistant":"Home Assistant","Guest expired":"Invitado caducado","Ready":"Listo","No tariff":"Sin tarifa","No solar":"Sin energía solar","No deadline":"Sin plazo","No charging goal":"Sin objetivo","Limited power":"Potencia limitada","No source":"Sin fuente","No capacity":"Sin capacidad","Wiring unknown":"Cableado desconocido","Guest":"Invitado","Charged":"Cargado","Charging":"Cargando","Stopped":"Detenido","Confirmed":"Confirmado","No action":"Sin acción","Reason":"Motivo","Energy":"Energía","Repeat":"Repetir","Measured session energy":"Energía medida de sesión","Last confirmed session":"Última sesión confirmada","Measured energy":"Energía medida","Verified cost":"Coste verificado","Current range":"Rango de corriente","Measured confirmation":"Confirmación medida","Control type":"Tipo de control","On/off":"Encendido/apagado","Variable current":"Corriente variable","Unverified":"No verificado","No charger assigned":"Sin punto asignado","Target battery %":"Batería objetivo %","Asset name":"Nombre del activo","Asset type":"Tipo de activo","Temporary guest":"Invitado temporal","Guest until":"Invitado hasta","Expected connection":"Conexión prevista","Save charging site":"Guardar instalación","Save sources":"Guardar fuentes","Maximum group kW":"Potencia máxima del grupo kW","Group power ceiling kW":"Límite del grupo kW","Site name":"Nombre del lugar","Parallel chargers":"Puntos simultáneos","Save electrical limits":"Guardar límites","Electrical limits":"Límites eléctricos","Battery data":"Datos de batería","Rated power":"Potencia nominal","Phases":"Fases","Active session":"Sesión activa","Add a chargeable asset":"Añadir activo de carga","Create asset":"Crear activo","Cancel adding":"Cancelar","Remove":"Eliminar","blue":"Azul","orange":"Naranja","green":"Verde","purple":"Morado","gold":"Dorado","teal":"Verde azulado","pink":"Rosa","indigo":"Índigo","olive":"Oliva","brown":"Marrón","coral":"Coral","slate":"Pizarra","violet":"Violeta","lime":"Lima","salmon":"Salmón","cyan":"Cian","wine":"Granate","forest":"Verde bosque","peach":"Melocotón","lavender":"Lavanda","turquoise":"Turquesa","rust":"Óxido","navy":"Azul marino","moss":"Verde musgo","Effective charging power":"Potencia efectiva de carga","Car":"Coche","Bicycle":"Bicicleta","Motorcycle":"Motocicleta","Scooter":"Patinete","Other":"Otro","No active plan":"Sin plan activo","Confirm connected vehicle":"Confirmar vehículo conectado","Connected vehicle":"Vehículo conectado","Not confirmed":"Sin confirmar"}};
function mcTr(value){
  const raw=String(value);
  return MC_TEXT[mcLanguage]?.[raw]||raw;
}
function mcOwnerColor(kind,id,configuration,palette){
  const rows=kind==="charger"?configuration?.chargers:configuration?.assets;
  const found=(rows||[]).find(x=>x.id===id);
  return found?.plan_color&&palette?.[found.plan_color]||
    "var(--secondary-text-color,#757d87)";
}

const MC_MODE_SELECT={
  Automatic:"automatic",Solar:"solar",Economy:"economy",
  "Ready By":"ready_by","Force Charge":"force_charge",Off:"off"
};
const MC_REASONS={
  DISCONNECTED:"Disconnected",CONNECTION_UNCONFIRMED:"Connection unknown",
  NO_CHARGEABLE_ASSET:"No vehicle",TEMPORARY_ASSET_EXPIRED:"Guest expired",
  OFF:"Off",PROPOSED:"Proposed",TARGET_MET:"Ready",PRICE_UNAVAILABLE:"No tariff",
  SOLAR_UNAVAILABLE:"No solar",DEADLINE_UNKNOWN:"No deadline",
  DEMAND_UNKNOWN:"Charging demand unknown",NO_CHARGING_GOAL:"No charging goal",
  BATTERY_CAPACITY_NOT_CONFIGURED:"Set battery capacity",CHARGE_EFFICIENCY_NOT_CONFIGURED:"Set charging efficiency",
  SOC_SOURCE_UNAVAILABLE:"Battery level unavailable",INSUFFICIENT_CAPACITY_OR_TIME:"Limited power",
  SOURCE_NOT_SELECTED:"No source",BINDING_CAPACITY_UNAVAILABLE:"No capacity",
  PHASE_WIRING_UNVERIFIED:"Wiring unknown",NO_ASSIGNED_ASSET:"No vehicle",
  VARIABLE_CURRENT_CAPABILITY_UNVERIFIED:"Check charger current range and wiring",
  CHARGER_CAPABILITY_UNQUALIFIED:"Check charger setup",
  CURRENT_RANGE_UNVERIFIED:"Check charger current range",
  ELECTRICAL_WIRING_UNVERIFIED:"Check charger phases and voltage",
  NATIVE_CURRENT_CAPABILITY_UNVERIFIED:"Check native current control",
  CURRENT_PLUG_ASSET_UNCONFIRMED:"Connection or assignment changed",
  EXTERNAL_WRITER_OWNS_CHARGER:"Inactive",
  CHARGER_INACTIVE:"Inactive",
  PHYSICAL_COMMISSIONING_REQUIRED:"Inactive",
  NATIVE_CURRENT_UNIT_UNSUPPORTED:"Current control must use A",
  PHYSICAL_CONNECTION_UNVERIFIED:"Connection not verified",
  INDEPENDENT_POWER_UNAVAILABLE:"Power measurement missing",
  NATIVE_SWITCH_REQUIRED:"Charger control missing",
  MANUAL_START_REQUIRES_FORCE_CHARGE:"Select Force Charge",
  CONTROL_STATE_UNVERIFIED:"Control state unverified",
  PREVIOUS_COMMAND_UNCONFIRMED:"Previous command unresolved",
  PHYSICAL_PHASES_UNVERIFIED:"Wiring unknown",
  NATIVE_SWITCH_UNAVAILABLE:"Charger unavailable",
  MANUAL_ONE_OFF_NOT_AVAILABLE:"Unavailable"

};
function mcReason(value){
  if(MC_REASONS[value])return mcTr(MC_REASONS[value]);
  // Unknown structured native reasons must not be disguised as a generic
  // 'Unavailable': preserve recoverable meaning without guessing success.
  if(typeof value==="string"&&/^[A-Z][A-Z0-9_]{2,100}$/.test(value)){
    return value.toLowerCase().replace(/_/g," ")
      .replace(/^./,first=>first.toUpperCase());
  }
  return mcTr("Unavailable");
}
const MC_TABS = ["Overview", "Charging Plan", "Chargeable Assets", "Chargers", "Settings"];
const MC_SETTINGS = ["Charging site", "Sources & bindings", "Charging strategy", "Safety & limits", "Integrations"];
// Pause is a persistent Charger admission hold, not a second strategy.
for (const [locale, terms] of Object.entries({
  nl:{"Pause charging":"Laden pauzeren","Resume charging":"Laden hervatten","Paused":"Gepauzeerd","Ready for next plan":"Klaar voor volgend laadplan"},
  fr:{"Pause charging":"Mettre en pause","Resume charging":"Reprendre","Paused":"En pause","Ready for next plan":"Prêt pour le prochain plan"},
  da:{"Pause charging":"Sæt opladning på pause","Resume charging":"Genoptag opladning","Paused":"Sat på pause","Ready for next plan":"Klar til næste plan"},
  nb:{"Pause charging":"Sett lading på pause","Resume charging":"Gjenoppta lading","Paused":"Pauset","Ready for next plan":"Klar for neste plan"},
  sv:{"Pause charging":"Pausa laddning","Resume charging":"Återuppta laddning","Paused":"Pausad","Ready for next plan":"Klar för nästa plan"},
  de:{"Pause charging":"Laden pausieren","Resume charging":"Laden fortsetzen","Paused":"Pausiert","Ready for next plan":"Bereit für den nächsten Plan"},
  es:{"Pause charging":"Pausar carga","Resume charging":"Reanudar carga","Paused":"En pausa","Ready for next plan":"Listo para el próximo plan"}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,translations] of Object.entries({
  nl:{"Configure in Home Assistant":"Configureren in Home Assistant","Selected":"Geselecteerd"},
  fr:{"Configure in Home Assistant":"Configurer dans Home Assistant","Selected":"Sélectionné"},
  da:{"Configure in Home Assistant":"Konfigurer i Home Assistant","Selected":"Valgt"},
  nb:{"Configure in Home Assistant":"Konfigurer i Home Assistant","Selected":"Valgt"},
  sv:{"Configure in Home Assistant":"Konfigurera i Home Assistant","Selected":"Vald"},
  de:{"Configure in Home Assistant":"In Home Assistant konfigurieren","Selected":"Ausgewählt"},
  es:{"Configure in Home Assistant":"Configurar en Home Assistant","Selected":"Seleccionado"}
}))Object.assign(MC_TEXT[locale],translations);
for(const [locale,label] of Object.entries({"nl":"Gemeten sessievermogen als prognose","fr":"Prévision selon la puissance mesurée de la session","da":"Prognose fra målt sessionseffekt","nb":"Prognose fra målt økteffekt","sv":"Prognos från uppmätt sessionseffekt","de":"Prognose aus gemessener Sitzungsleistung","es":"Previsión según la potencia medida de la sesión"}))MC_TEXT[locale]["Forecast from measured session power"]=label;
for(const [locale,label] of Object.entries({"nl":"Geplande laadkosten","fr":"Coût de recharge prévu","da":"Planlagte ladeomkostninger","nb":"Planlagt ladekostnad","sv":"Planerad laddkostnad","de":"Geplante Ladekosten","es":"Coste de carga previsto"}))MC_TEXT[locale]["Planned charging cost"]=label;
for(const [locale,labels] of Object.entries({"nl":["Actuele sessiekosten","Laatste sessiekosten"],"fr":["Coût de la session active","Coût de la dernière session"],"da":["Aktuelle sessionsomkostninger","Seneste sessionsomkostninger"],"nb":["Kostnad for aktiv økt","Kostnad for siste økt"],"sv":["Pågående sessionskostnad","Senaste sessionskostnad"],"de":["Aktuelle Sitzungskosten","Letzte Sitzungskosten"],"es":["Coste de sesión activa","Coste de última sesión"]})){
  MC_TEXT[locale]["Active session cost"]=labels[0];
  MC_TEXT[locale]["Last session cost"]=labels[1];
}
for(const [locale,labels] of Object.entries({"nl":["Laadkosten vandaag","Laadkosten deze maand","Laadkosten dit jaar","Gemiddelde laadprijs vandaag","Gemiddelde laadprijs deze maand","Gemiddelde laadprijs dit jaar","Gemiddelde laadprijs","Gedeeltelijke dekking","Dagen gecontroleerd"],"fr":["Coût de recharge aujourd’hui","Coût de recharge ce mois","Coût de recharge cette année","Prix moyen de recharge aujourd’hui","Prix moyen de recharge ce mois","Prix moyen de recharge cette année","Prix moyen de recharge","Couverture partielle","Jours vérifiés"],"da":["Ladeomkostninger i dag","Ladeomkostninger denne måned","Ladeomkostninger i år","Gennemsnitlig ladepris i dag","Gennemsnitlig ladepris denne måned","Gennemsnitlig ladepris i år","Gennemsnitlig ladepris","Delvis dækning","Kontrollerede dage"],"nb":["Ladekostnad i dag","Ladekostnad denne måneden","Ladekostnad i år","Gjennomsnittlig ladepris i dag","Gjennomsnittlig ladepris denne måneden","Gjennomsnittlig ladepris i år","Gjennomsnittlig ladepris","Delvis dekning","Kontrollerte dager"],"sv":["Laddkostnad i dag","Laddkostnad denna månad","Laddkostnad i år","Genomsnittligt laddpris i dag","Genomsnittligt laddpris denna månad","Genomsnittligt laddpris i år","Genomsnittligt laddpris","Delvis täckning","Kontrollerade dagar"],"de":["Ladekosten heute","Ladekosten diesen Monat","Ladekosten dieses Jahr","Durchschnittlicher Ladepreis heute","Durchschnittlicher Ladepreis diesen Monat","Durchschnittlicher Ladepreis dieses Jahr","Durchschnittlicher Ladepreis","Teilweise Abdeckung","Geprüfte Tage"],"es":["Coste de carga hoy","Coste de carga este mes","Coste de carga este año","Precio medio de carga hoy","Precio medio de carga este mes","Precio medio de carga este año","Precio medio de carga","Cobertura parcial","Días comprobados"]})){
  for(const [i,key] of ["Charging cost today","Charging cost this month","Charging cost this year","Average charging price today","Average charging price this month","Average charging price this year","Average charging price","Partial coverage","Days checked"].entries())MC_TEXT[locale][key]=labels[i];
}
for(const [locale,label] of Object.entries({"nl":"Indicatieve laadkosten","fr":"Coût de recharge indicatif","da":"Indikative ladeomkostninger","nb":"Indikativ ladekostnad","sv":"Indikativ laddkostnad","de":"Indikative Ladekosten","es":"Coste de carga indicativo"}))MC_TEXT[locale]["Indicative charging cost"]=label;
for(const [locale,label] of Object.entries({"nl":"Laadkosten","fr":"Coûts de recharge","da":"Ladeomkostninger","nb":"Ladekostnader","sv":"Laddkostnader","de":"Ladekosten","es":"Costes de carga"}))MC_TEXT[locale]["Charging costs"]=label;
for(const [locale,labels] of Object.entries({
  nl:["Vaste toewijzing","Vast toewijzen","Aansluiting bevestigen","Gedeelde laadpaal","Vaste voertuigtoewijzing","Gebruik vaste toewijzing alleen als deze laadpaal voor deze wagen is gereserveerd. Wijzig eerst de toewijzing voor andere wagens."],
  fr:["Affectation fixe","Utiliser une affectation fixe","Exiger la confirmation","Borne partagée","Véhicule affecté en permanence","Réservez cette borne à ce véhicule. Modifiez l’affectation avant de brancher un autre véhicule."],
  de:["Feste Zuordnung","Fest zuordnen","Anschluss bestätigen","Geteilte Ladestation","Feste Fahrzeugzuordnung","Nur für dieses Fahrzeug reservierte Ladestationen fest zuordnen. Vor einem anderen Fahrzeug die Zuordnung ändern."],
  es:["Asignación fija","Usar asignación fija","Confirmar conexión","Cargador compartido","Vehículo fijo","Reserve este cargador para este vehículo. Cambie la asignación antes de conectar otro vehículo."],
  da:["Fast tildeling","Brug fast tildeling","Kræv bekræftelse","Delt lader","Fast køretøj","Reserver laderen til dette køretøj. Skift tildeling før et andet køretøj tilsluttes."],
  nb:["Fast tildeling","Bruk fast tildeling","Krev bekreftelse","Delt lader","Fast kjøretøy","Reserver laderen for dette kjøretøyet. Endre tildelingen før et annet kjøretøy kobles til."],
  sv:["Fast tilldelning","Använd fast tilldelning","Kräv bekräftelse","Delad laddare","Fast fordon","Reservera laddaren för detta fordon. Ändra tilldelningen innan ett annat fordon ansluts."]
})){
  ["Fixed assignment","Use fixed assignment","Require plug confirmation","Shared charger","Fixed vehicle assignment","Use fixed assignment only when this charger is reserved for this vehicle. Other vehicles require changing the assignment first."].forEach((key,i)=>MC_TEXT[locale][key]=labels[i]);
}
for(const [locale,labels] of Object.entries({nl:["Rust","Probleem"],fr:["En attente","Problème"],da:["I ro","Problem"],nb:["Inaktiv","Problem"],sv:["Vilande","Problem"],de:["Ruhezustand","Problem"],es:["En reposo","Problema"]})){
  MC_TEXT[locale]["Idle"]=labels[0];MC_TEXT[locale]["Problem"]=labels[1];
}
for(const [locale,label] of Object.entries({nl:"Enkel schatting op nominaal vermogen",fr:"Estimation sur puissance nominale uniquement",da:"Kun estimat ved nominel effekt",nb:"Kun estimat ved nominell effekt",sv:"Endast uppskattning med nominell effekt",de:"Nur Schätzung anhand der Nennleistung",es:"Estimación solo con potencia nominal"}))MC_TEXT[locale]["Nominal power estimate only"]=label;
for(const [locale,label] of Object.entries({nl:"Aangenomen minimum planningsvermogen",fr:"Puissance minimale de planification supposée",da:"Antaget minimal planlægningseffekt",nb:"Antatt minste planleggingseffekt",sv:"Antagen lägsta planeringseffekt",de:"Angenommene Mindestplanungsleistung",es:"Potencia mínima de planificación supuesta"}))MC_TEXT[locale]["Assumed minimum planning power"]=label;
for(const [locale,label] of Object.entries({nl:"Deadlineherstel · hogere geverifieerde stroom, werkelijk vermogen kan afwijken",fr:"Rattrapage de l’échéance · consigne vérifiée supérieure, puissance réelle variable",da:"Fristgenopretning · højere verificeret strøm, faktisk effekt kan afvige",nb:"Fristinnhenting · høyere verifisert strøm, faktisk effekt kan avvike",sv:"Återhämtning inför tidsgräns · högre verifierad ström, faktisk effekt kan avvika",de:"Terminaufholung · höherer geprüfter Sollwert, tatsächliche Leistung kann abweichen",es:"Recuperación del plazo · consigna superior verificada, potencia real variable"}))MC_TEXT[locale]["Deadline recovery · higher verified setpoint, actual draw may differ"]=label;
for(const [locale,label] of Object.entries({nl:"Conservatief plan · beschikbare boost",fr:"Plan prudent · puissance supplémentaire disponible",da:"Konservativ plan · tilgængeligt boost",nb:"Konservativ plan · tilgjengelig boost",sv:"Konservativ plan · tillgänglig ökning",de:"Konservativer Plan · verfügbare Mehrleistung",es:"Plan conservador · potencia adicional disponible"}))MC_TEXT[locale]["Conservative plan · available boost"]=label;
// Native setup and observed-session labels reuse the existing card locale map.
for(const [locale,terms] of Object.entries({"nl":{"Review charger setup":"Laadpaalconfiguratie","Save charger setup":"Configuratie opslaan","Discover native sources":"Native bronnen zoeken","Native device current range":"Stroomgebied apparaat","Configured current range":"Ingesteld stroomgebied","Effective current range":"Effectief stroomgebied","Observed charging now":"Laden gemeten","Observed charging run":"Gemeten laadsessie","Earlier observed runs":"Eerdere gemeten sessies","Power-derived energy":"Energie uit vermogen","Average power":"Gemiddeld vermogen","Peak power":"Piekvermogen","Estimated energy cost":"Geschatte energiekosten","Verified energy cost":"Bevestigde energiekosten","Electrical limits & optional sources":"Elektrische limieten en optionele bronnen","Stop charging with the current owner before changing activation":"Stop het laden via de huidige eigenaar vóór activering","Incomplete start/end or source coverage · observed portion only":"Onvolledig begin/einde of brongegevens · alleen gemeten deel","Save not confirmed; refresh and retry":"Opslaan niet bevestigd; vernieuw en probeer opnieuw","suggestions":"voorstellen"},"fr":{"Review charger setup":"Configuration de la borne","Save charger setup":"Enregistrer la configuration","Discover native sources":"Détecter les sources natives","Native device current range":"Plage native de courant","Configured current range":"Plage de courant configurée","Effective current range":"Plage effective de courant","Observed charging now":"Charge observée en cours","Observed charging run":"Charge observée","Earlier observed runs":"Charges précédentes observées","Power-derived energy":"Énergie déduite de la puissance","Average power":"Puissance moyenne","Peak power":"Puissance de pointe","Estimated energy cost":"Coût énergétique estimé","Verified energy cost":"Coût énergétique confirmé","Electrical limits & optional sources":"Limites électriques et sources facultatives","Stop charging with the current owner before changing activation":"Arrêtez la charge via le contrôleur actuel avant activation","Incomplete start/end or source coverage · observed portion only":"Début/fin ou données incomplets · portion observée uniquement","Save not confirmed; refresh and retry":"Enregistrement non confirmé ; actualisez et réessayez","suggestions":"suggestions"},"de":{"Review charger setup":"Ladepunkt konfigurieren","Save charger setup":"Konfiguration speichern","Discover native sources":"Native Quellen suchen","Native device current range":"Nativer Strombereich","Configured current range":"Konfigurierter Strombereich","Effective current range":"Effektiver Strombereich","Observed charging now":"Aktuell beobachtete Ladung","Observed charging run":"Beobachteter Ladevorgang","Earlier observed runs":"Frühere beobachtete Vorgänge","Power-derived energy":"Energie aus Leistung","Average power":"Durchschnittsleistung","Peak power":"Spitzenleistung","Estimated energy cost":"Geschätzte Energiekosten","Verified energy cost":"Bestätigte Energiekosten","Electrical limits & optional sources":"Elektrische Grenzen und optionale Quellen","Stop charging with the current owner before changing activation":"Ladevorgang über den aktuellen Besitzer vor Aktivierung stoppen","Incomplete start/end or source coverage · observed portion only":"Start/Ende oder Quellen unvollständig · nur beobachteter Abschnitt","Save not confirmed; refresh and retry":"Speichern nicht bestätigt; aktualisieren und erneut versuchen","suggestions":"Vorschläge"},"es":{"Review charger setup":"Configurar cargador","Save charger setup":"Guardar configuración","Discover native sources":"Buscar fuentes nativas","Native device current range":"Rango de corriente nativo","Configured current range":"Rango de corriente configurado","Effective current range":"Rango de corriente efectivo","Observed charging now":"Carga observada en curso","Observed charging run":"Carga observada","Earlier observed runs":"Cargas observadas anteriores","Power-derived energy":"Energía derivada de potencia","Average power":"Potencia media","Peak power":"Potencia máxima","Estimated energy cost":"Coste energético estimado","Verified energy cost":"Coste energético confirmado","Electrical limits & optional sources":"Límites eléctricos y fuentes opcionales","Stop charging with the current owner before changing activation":"Detenga la carga con el controlador actual antes de activar","Incomplete start/end or source coverage · observed portion only":"Inicio/fin o datos incompletos · solo tramo observado","Save not confirmed; refresh and retry":"Guardado no confirmado; actualice e inténtelo de nuevo","suggestions":"sugerencias"},"da":{"Review charger setup":"Konfigurer lader","Save charger setup":"Gem konfiguration","Discover native sources":"Find native kilder","Native device current range":"Enhedens strømområde","Configured current range":"Konfigureret strømområde","Effective current range":"Effektivt strømområde","Observed charging now":"Observeret opladning nu","Observed charging run":"Observeret opladning","Earlier observed runs":"Tidligere observerede opladninger","Power-derived energy":"Energi ud fra effekt","Average power":"Gennemsnitseffekt","Peak power":"Spidseffekt","Estimated energy cost":"Estimeret energiomkostning","Verified energy cost":"Bekræftet energiomkostning","Electrical limits & optional sources":"Elektriske grænser og valgfrie kilder","Stop charging with the current owner before changing activation":"Stop opladning via nuværende ejer før aktivering","Incomplete start/end or source coverage · observed portion only":"Ufuldstændig start/slut eller kildedata · kun observeret del","Save not confirmed; refresh and retry":"Lagring ikke bekræftet; opdater og prøv igen","suggestions":"forslag"},"nb":{"Review charger setup":"Konfigurer lader","Save charger setup":"Lagre konfigurasjon","Discover native sources":"Finn native kilder","Native device current range":"Enhetens strømområde","Configured current range":"Konfigurert strømområde","Effective current range":"Effektivt strømområde","Observed charging now":"Observert lading nå","Observed charging run":"Observert lading","Earlier observed runs":"Tidligere observerte ladinger","Power-derived energy":"Energi fra effekt","Average power":"Gjennomsnittlig effekt","Peak power":"Toppeffekt","Estimated energy cost":"Estimert energikostnad","Verified energy cost":"Bekreftet energikostnad","Electrical limits & optional sources":"Elektriske grenser og valgfrie kilder","Stop charging with the current owner before changing activation":"Stopp lading via nåværende eier før aktivering","Incomplete start/end or source coverage · observed portion only":"Ufullstendig start/slutt eller kildedata · bare observert del","Save not confirmed; refresh and retry":"Lagring ikke bekreftet; oppdater og prøv igjen","suggestions":"forslag"},"sv":{"Review charger setup":"Konfigurera laddare","Save charger setup":"Spara konfiguration","Discover native sources":"Hitta inbyggda källor","Native device current range":"Enhetens strömområde","Configured current range":"Konfigurerat strömområde","Effective current range":"Effektivt strömområde","Observed charging now":"Observerad laddning nu","Observed charging run":"Observerad laddning","Earlier observed runs":"Tidigare observerade laddningar","Power-derived energy":"Energi från effekt","Average power":"Medeleffekt","Peak power":"Toppeffekt","Estimated energy cost":"Beräknad energikostnad","Verified energy cost":"Bekräftad energikostnad","Electrical limits & optional sources":"Elektriska gränser och valfria källor","Stop charging with the current owner before changing activation":"Stoppa laddning via nuvarande ägare före aktivering","Incomplete start/end or source coverage · observed portion only":"Ofullständig start/slut eller källdata · endast observerad del","Save not confirmed; refresh and retry":"Sparande inte bekräftat; uppdatera och försök igen","suggestions":"förslag"}}))
  Object.assign(MC_TEXT[locale],terms);

// One Asset-side chooser; all writes still target the Charger-owned Config Entry.
for(const [locale,terms] of Object.entries({
  nl:{"Assign charger":"Laadpaal toewijzen","Change charger":"Laadpaal wijzigen","Select charger":"Kies laadpaal","Assign selected charger":"Laadpaal toewijzen","Unassign charger":"Laadpaal loskoppelen","No free charger":"Geen vrije laadpaal","Close assignment":"Sluiten","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Alleen bij stilstand. Stop het laden apart vóór de overdracht."},
  fr:{"Assign charger":"Attribuer une borne","Change charger":"Changer de borne","Select charger":"Choisir une borne","Assign selected charger":"Attribuer cette borne","Unassign charger":"Désattribuer la borne","No free charger":"Aucune borne libre","Close assignment":"Fermer","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Uniquement à l'arrêt. Arrêtez la recharge avant de déplacer un véhicule."},
  da:{"Assign charger":"Tildel lader","Change charger":"Skift lader","Select charger":"Vælg lader","Assign selected charger":"Tildel valgt lader","Unassign charger":"Fjern tilknytning","No free charger":"Ingen ledig lader","Close assignment":"Luk","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Kun ved stilstand. Stop opladning før flytning af køretøjet."},
  nb:{"Assign charger":"Tildel lader","Change charger":"Bytt lader","Select charger":"Velg lader","Assign selected charger":"Tildel valgt lader","Unassign charger":"Fjern tilordning","No free charger":"Ingen ledig lader","Close assignment":"Lukk","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Bare når laderne er stoppet. Stopp lading før flytting."},
  sv:{"Assign charger":"Tilldela laddare","Change charger":"Byt laddare","Select charger":"Välj laddare","Assign selected charger":"Tilldela vald laddare","Unassign charger":"Ta bort tilldelning","No free charger":"Ingen ledig laddare","Close assignment":"Stäng","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Endast i viloläge. Stoppa laddning före flytt."},
  de:{"Assign charger":"Ladepunkt zuweisen","Change charger":"Ladepunkt wechseln","Select charger":"Ladepunkt auswählen","Assign selected charger":"Ladepunkt zuweisen","Unassign charger":"Zuweisung aufheben","No free charger":"Kein freier Ladepunkt","Close assignment":"Schließen","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Nur im Stillstand. Laden vor dem Wechsel separat stoppen."},
  es:{"Assign charger":"Asignar cargador","Change charger":"Cambiar cargador","Select charger":"Elegir cargador","Assign selected charger":"Asignar cargador elegido","Unassign charger":"Quitar asignación","No free charger":"No hay cargadores libres","Close assignment":"Cerrar","Idle-only reassignment. Stop charging separately before moving a vehicle.":"Solo en reposo. Detenga la carga antes de cambiar el vehículo."}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,terms] of Object.entries({
  nl:{"Stop charging before changing charger":"Stop eerst met laden voordat je van laadpaal wisselt","Settings changed; refresh and retry":"Instellingen gewijzigd; vernieuw en probeer opnieuw"},
  fr:{"Stop charging before changing charger":"Arrêtez la charge avant de changer de borne","Settings changed; refresh and retry":"Paramètres modifiés ; actualisez et réessayez"},
  da:{"Stop charging before changing charger":"Stop opladning før skift af lader","Settings changed; refresh and retry":"Indstillinger ændret; opdater og prøv igen"},
  nb:{"Stop charging before changing charger":"Stopp lading før bytte av lader","Settings changed; refresh and retry":"Innstillinger endret; oppdater og prøv igjen"},
  sv:{"Stop charging before changing charger":"Stoppa laddning innan du byter laddare","Settings changed; refresh and retry":"Inställningarna har ändrats; uppdatera och försök igen"},
  de:{"Stop charging before changing charger":"Laden vor dem Ladepunktwechsel stoppen","Settings changed; refresh and retry":"Einstellungen geändert; aktualisieren und erneut versuchen"},
  es:{"Stop charging before changing charger":"Detenga la carga antes de cambiar de cargador","Settings changed; refresh and retry":"La configuración cambió; actualice e inténtelo de nuevo"}
}))Object.assign(MC_TEXT[locale],terms);
for(const [locale,translation] of Object.entries({"nl":"Wijs eerst het andere voertuig af","fr":"Désattribuez d'abord l'autre véhicule","da":"Fjern først det andet køretøjs tilknytning","nb":"Fjern tilordningen for det andre kjøretøyet først","sv":"Ta först bort det andra fordonets tilldelning","de":"Zuerst die Zuweisung des anderen Fahrzeugs aufheben","es":"Quite primero la asignación del otro vehículo"}))
  MC_TEXT[locale]["Unassign the other vehicle first"]=translation;
const keysForMinimalCharger=["Start unavailable","External charging controller","Verify charger safety","Connection not verified","Power measurement missing","Charger control missing","Select Force Charge","Control state unverified","Previous command unresolved","Charger unavailable"];
for(const [locale,labels] of Object.entries({"nl":["Start niet beschikbaar","Externe laadsturing actief","Controleer eerst de veiligheid van de laadpaal","Aansluiting niet bevestigd","Vermogensmeting ontbreekt","Laadsturing ontbreekt","Selecteer Force Charge","Controlestatus onbekend","Vorige opdracht onbeslist","Laadpaal niet beschikbaar"],"fr":["Démarrage indisponible","Contrôleur de charge externe","Vérifier la sécurité de la borne","Connexion non vérifiée","Mesure de puissance absente","Commande de borne absente","Choisir Force Charge","État de commande non vérifié","Commande précédente non résolue","Borne indisponible"],"da":["Start ikke tilgængelig","Ekstern ladestyring","Kontroller laderens sikkerhed","Forbindelse ikke bekræftet","Effektmåling mangler","Ladestyring mangler","Vælg Force Charge","Styringstilstand ukendt","Tidligere kommando uafklaret","Lader utilgængelig"],"nb":["Start ikke tilgjengelig","Ekstern ladekontroll","Bekreft laderens sikkerhet","Tilkobling ikke bekreftet","Effektmåling mangler","Ladekontroll mangler","Velg Force Charge","Kontrollstatus ubekreftet","Forrige kommando uavklart","Lader utilgjengelig"],"sv":["Start ej tillgänglig","Extern laddstyrning","Verifiera laddarens säkerhet","Anslutning ej bekräftad","Effektmätning saknas","Laddstyrning saknas","Välj Force Charge","Styrstatus ej verifierad","Föregående kommando olöst","Laddare otillgänglig"],"de":["Start nicht verfügbar","Externe Ladesteuerung","Sicherheit des Ladepunkts prüfen","Verbindung nicht bestätigt","Leistungsmessung fehlt","Ladesteuerung fehlt","Force Charge auswählen","Steuerstatus ungeprüft","Vorheriger Befehl ungeklärt","Ladepunkt nicht verfügbar"],"es":["Inicio no disponible","Control de carga externo","Verifique la seguridad del cargador","Conexión no verificada","Falta medición de potencia","Falta control del cargador","Seleccione Force Charge","Estado de control no verificado","Comando anterior sin resolver","Cargador no disponible"]}))
  keysForMinimalCharger.forEach((key,i)=>{MC_TEXT[locale][key]=labels[i];});
for(const [locale,terms] of Object.entries({"nl":["Indicatieve variabele energiekosten","Schatting op basis van gemeten vermogen, geen factuur"],"fr":["Coût énergétique variable indicatif","Estimation fondée sur la puissance mesurée, pas une facture"],"de":["Geschätzte variable Energiekosten","Aus Messleistung berechnete Schätzung, keine Rechnung"],"es":["Coste variable de energía estimado","Estimación de potencia medida, no es una factura"],"da":["Anslået variabel energiomkostning","Estimat fra målt effekt, ikke en faktura"],"nb":["Anslått variabel energikostnad","Estimat fra målt effekt, ikke en faktura"],"sv":["Beräknad rörlig energikostnad","Uppskattning från uppmätt effekt, inte en faktura"]})){
  MC_TEXT[locale]["Indicative variable energy cost"]=terms[0];
  MC_TEXT[locale]["Power-derived estimate, not a bill"]=terms[1];
}
for(const [locale,labels] of Object.entries({"nl":["Variabel referentietarief","Spotprijs"],"fr":["Prix de référence variable","Prix spot"],"de":["Variabler Referenzpreis","Spotpreis"],"es":["Precio variable de referencia","Precio spot"],"da":["Variabel referencepris","Spotpris"],"nb":["Variabel referansepris","Spotpris"],"sv":["Rörligt referenspris","Spotpris"]})){
  MC_TEXT[locale]["Variable reference price"]=labels[0];
  MC_TEXT[locale]["Spot price"]=labels[1];
}
for(const [locale,b] of Object.entries({
  nl:["Conservatieve bovengrens budget","Budget resterend (conservatief)","Budgetvoortgang"],
  fr:["Plafond prudent du budget","Budget restant (prudent)","Suivi du budget"],
  da:["Konservativ budgetgrænse","Resterende budget (konservativt)","Budgetforbrug"],
  nb:["Konservativ budsjettgrense","Resterende budsjett (konservativt)","Budsjettfremdrift"],
  sv:["Konservativ budgetgräns","Återstående budget (konservativt)","Budgetförbrukning"],
  de:["Konservative Budgetobergrenze","Restbudget (konservativ)","Budgetfortschritt"],
  es:["Límite superior conservador","Presupuesto restante (prudente)","Progreso del presupuesto"]
})){
  for(const [i,key] of ["Conservative budget upper bound",
     "Budget remaining (conservative)","Budget progress"].entries())
    MC_TEXT[locale][key]=b[i];
}
for(const [locale,b] of Object.entries({
  nl:["Laadpatroon","Flexibele goedkoopste kwartieren","Eén aaneengesloten laadsessie",
      "Aaneengesloten laden en prijsstrategie"],
  fr:["Mode de recharge","Créneaux les moins chers","Une recharge continue",
      "Continuité et stratégie tarifaire"],
  da:["Lademønster","Billigste fleksible kvarter","Én sammenhængende opladning",
      "Kontinuitet og prisstrategi"],
  nb:["Lademønster","Billigste fleksible kvarter","Én sammenhengende lading",
      "Kontinuitet og prisstrategi"],
  sv:["Laddmönster","Billigaste flexibla kvartarna","En sammanhängande laddning",
      "Kontinuitet och prisstrategi"],
  de:["Lademuster","Flexible günstigste Viertelstunden","Ein durchgehender Ladevorgang",
      "Kontinuität und Preisstrategie"],
  es:["Patrón de carga","Intervalos flexibles más baratos","Una carga continua",
      "Continuidad y estrategia de precio"]
})){
  for(const [i,key] of ["Charging pattern","Flexible cheapest quarters",
    "One continuous charge","Continuity and price strategy"].entries())
    MC_TEXT[locale][key]=b[i];
}
for(const [locale,b] of Object.entries({
  nl:["Minimum laden vóór prijsgrens","Prijsplafond per kWh",
      "Onmiddellijk laden bij lage prijs","Onmiddellijk laden bij lage SoC",
      "Opportunistisch percentage","Prijsvaluta","Kies eerst de valuta",
      "Stel valuta in","Vroegste start instellen","Opportunistisch laden",
      "Type 1 — fractie van prijsplafond","Type 2 — prijs volgende dag"],
  fr:["Minimum avant le plafond","Plafond de prix par kWh",
      "Seuil de prix bas immédiat","Seuil batterie faible immédiat",
      "Pourcentage opportuniste","Devise tarifaire","Choisir d'abord la devise",
      "Choisir la devise","Définir le début le plus tôt","Charge opportuniste",
      "Type 1 — fraction du plafond","Type 2 — prix de demain"],
  de:["Mindestladung vor Preislimit","Preislimit pro kWh",
      "Sofortladen bei Niedrigpreis","Sofortladen bei niedrigem Akkustand",
      "Opportunistischer Prozentsatz","Preiswährung","Zuerst Währung wählen",
      "Währung einstellen","Frühester Start","Opportunistisches Laden",
      "Typ 1 — Preislimitanteil","Typ 2 — morgiger Preis"]
})){
  for(const [i,key] of ["Minimum charge before price limits","Price ceiling per kWh",
    "Immediate low-price threshold","Immediate low-SoC threshold",
    "Opportunistic percentage","Price currency",
    "Choose currency before price limits","Set price currency",
    "Set earliest start","Opportunistic charging",
    "Type 1 — cap fraction","Type 2 — tomorrow price"].entries())
    MC_TEXT[locale][key]=b[i];
}
const MC_NOVICE_UX_WORDS=["All charging · Power & price","Shaded planned · outlined accepted · solid measured · price line","Power","Price unavailable","reference price, not an invoice","Price intervals incomplete; missing periods are not zero","Still planned","charger","chargers","Charging per vehicle and charger","No qualified physical or planned power in this period","Set charging goal","I want to charge to","Battery target (%)","Extra energy (kWh)","Charging time (minutes)","Charging budget (€)","Amount","Save charging goal","Indicative energy budget, not a guaranteed electricity bill","Schedule charging","Hide charging schedule","When should the vehicle be ready?","Set one-time or daily Ready By","Add guest or vehicle","Charging pattern","Price ceiling per kWh","Next charge","Shortfall","Measured power is attributed to this charger; vehicle may be unknown","No qualified timeline"];
for(const [locale,translations] of Object.entries({"nl":["Totaal laden · Vermogen en prijs","Transparant gepland · omlijnd bevestigd · gevuld gemeten · prijslijn","Vermogen","Prijs niet beschikbaar","referentieprijs, geen factuur","Prijsperioden onvolledig; ontbrekende waarden zijn niet nul","Nog gepland","laadpaal","laadpalen","Laden per voertuig en laadpaal","Geen bevestigd gemeten of gepland vermogen in deze periode","Laaddoel instellen","Ik wil laden tot","Batterijdoel (%)","Extra energie (kWh)","Laadduur (minuten)","Laadbudget (€)","Hoeveelheid","Laaddoel opslaan","Indicatief energiebudget, geen gegarandeerde stroomfactuur","Laadtijden instellen","Laadtijden verbergen","Wanneer moet het voertuig klaar zijn?","Eenmalig of dagelijks gereed instellen","Gast of voertuig toevoegen","Laadpatroon","Maximumprijs per kWh","Volgende laadbeurt","Tekort","Gemeten vermogen hoort bij deze laadpaal; voertuig kan onbekend zijn","Geen bevestigde tijdlijn"],"fr":["Recharge totale · Puissance et prix","Prévu en transparence · accepté en contour · mesuré en plein · courbe de prix","Puissance","Prix indisponible","prix indicatif, pas une facture","Créneaux de prix incomplets ; absence ne signifie pas zéro","Encore prévu","borne","bornes","Recharge par véhicule et borne","Aucune puissance mesurée ou planifiée vérifiée pour cette période","Définir l'objectif de charge","Je veux charger jusqu'à","Batterie cible (%)","Énergie supplémentaire (kWh)","Durée de charge (minutes)","Budget de charge (€)","Quantité","Enregistrer l'objectif","Budget énergétique indicatif, pas une facture garantie","Programmer la charge","Masquer le calendrier","Quand le véhicule doit-il être prêt ?","Définir une échéance unique ou quotidienne","Ajouter un invité ou véhicule","Mode de charge","Prix maximal par kWh","Prochaine charge","Manque","Puissance mesurée attribuée à la borne ; véhicule éventuellement inconnu","Aucune chronologie qualifiée"],"de":["Gesamtladen · Leistung und Preis","Schattiert geplant · umrandet bestätigt · voll gemessen · Preislinie","Leistung","Preis nicht verfügbar","Referenzpreis, keine Rechnung","Preisintervalle unvollständig; fehlende Werte sind nicht null","Noch geplant","Ladepunkt","Ladepunkte","Laden nach Fahrzeug und Ladepunkt","Keine bestätigte Ladeleistung oder Planung in diesem Zeitraum","Ladeziel festlegen","Ich möchte laden bis","Batterieziel (%)","Zusätzliche Energie (kWh)","Ladedauer (Minuten)","Ladebudget (€)","Menge","Ladeziel speichern","Unverbindliches Energiebudget, keine garantierte Stromrechnung","Ladezeiten planen","Ladezeiten ausblenden","Wann soll das Fahrzeug bereit sein?","Einmalige oder tägliche Zielzeit","Gast oder Fahrzeug hinzufügen","Lademuster","Höchstpreis pro kWh","Nächste Ladung","Fehlmenge","Messleistung gehört zum Ladepunkt; Fahrzeug kann unbekannt sein","Keine qualifizierte Zeitachse"],"es":["Carga total · Potencia y precio","Sombreado planificado · contorno aceptado · sólido medido · línea de precio","Potencia","Precio no disponible","precio de referencia, no una factura","Intervalos de precio incompletos; lo desconocido no es cero","Aún previsto","cargador","cargadores","Carga por vehículo y cargador","No hay potencia medida ni planificada verificada en este período","Definir objetivo de carga","Quiero cargar hasta","Objetivo batería (%)","Energía extra (kWh)","Tiempo de carga (minutos)","Presupuesto de carga (€)","Cantidad","Guardar objetivo de carga","Presupuesto energético orientativo, no una factura garantizada","Programar carga","Ocultar horarios","¿Cuándo debe estar listo el vehículo?","Definir hora única o diaria","Añadir invitado o vehículo","Patrón de carga","Precio máximo por kWh","Siguiente carga","Déficit","La potencia medida corresponde al cargador; el vehículo puede ser desconocido","No hay cronología verificada"],"da":["Samlet opladning · Effekt og pris","Skygget planlagt · omridset godkendt · udfyldt målt · prislinje","Effekt","Pris utilgængelig","referencepris, ikke en faktura","Prisintervaller ufuldstændige; ukendt er ikke nul","Stadig planlagt","lader","ladere","Opladning pr. køretøj og lader","Ingen verificeret målt eller planlagt effekt i perioden","Indstil lademål","Jeg vil lade op til","Batterimål (%)","Ekstra energi (kWh)","Ladetid (minutter)","Ladebudget (€)","Mængde","Gem lademål","Vejledende energibudget, ikke en garanteret elregning","Planlæg opladning","Skjul ladeplan","Hvornår skal bilen være klar?","Indstil engangs- eller dagligt klar-tidspunkt","Tilføj gæst eller køretøj","Lademønster","Maksimumpris pr. kWh","Næste opladning","Mangel","Målt effekt tilhører laderen; køretøjet kan være ukendt","Ingen kvalificeret tidslinje"],"nb":["Samlet lading · Effekt og pris","Skygget planlagt · omrisset godkjent · fylt målt · prislinje","Effekt","Pris utilgjengelig","referansepris, ikke en faktura","Prisintervaller ufullstendige; ukjent er ikke null","Fortsatt planlagt","lader","ladere","Lading per kjøretøy og lader","Ingen verifisert målt eller planlagt effekt i perioden","Sett lademål","Jeg vil lade til","Batterimål (%)","Ekstra energi (kWh)","Ladetid (minutter)","Ladebudsjett (€)","Mengde","Lagre lademål","Veiledende energibudsjett, ikke garantert strømregning","Planlegg lading","Skjul ladeplan","Når må bilen være klar?","Sett engangs- eller daglig klartid","Legg til gjest eller kjøretøy","Lademønster","Makspris per kWh","Neste lading","Underskudd","Målt effekt gjelder laderen; kjøretøy kan være ukjent","Ingen kvalifisert tidslinje"],"sv":["Total laddning · Effekt och pris","Skuggat planerat · kontur accepterat · fyllt uppmätt · prislinje","Effekt","Pris saknas","referenspris, inte en faktura","Prisintervall ofullständiga; saknat värde är inte noll","Återstår planerat","laddare","laddare","Laddning per fordon och laddare","Ingen verifierad uppmätt eller planerad effekt under perioden","Ange laddmål","Jag vill ladda till","Batterimål (%)","Extra energi (kWh)","Laddtid (minuter)","Laddbudget (€)","Belopp","Spara laddmål","Ungefärlig energibudget, ingen garanterad elräkning","Schemalägg laddning","Dölj laddschema","När ska fordonet vara klart?","Ställ in engångs- eller daglig klartid","Lägg till gäst eller fordon","Laddmönster","Maxpris per kWh","Nästa laddning","Underskott","Uppmätt effekt tillhör laddaren; fordonet kan vara okänt","Ingen kvalificerad tidslinje"]})){
  MC_NOVICE_UX_WORDS.forEach((key,index)=>{MC_TEXT[locale][key]=translations[index];});
}
const MC_DAY_NAMES={
  mon:"Monday",tue:"Tuesday",wed:"Wednesday",thu:"Thursday",
  fri:"Friday",sat:"Saturday",sun:"Sunday"
};
for(const [locale,terms] of Object.entries({
  nl:{"Once":"Eenmalig","Daily":"Dagelijks","Specific days":"Specifieke dagen",
    "Monday":"Maandag","Tuesday":"Dinsdag","Wednesday":"Woensdag",
    "Thursday":"Donderdag","Friday":"Vrijdag","Saturday":"Zaterdag","Sunday":"Zondag",
    "Allowed charging times":"Toegestane laaduren","Charging days":"Laaddagen",
    "No day selected":"Dag niet geselecteerd","Window enabled":"Venster actief",
    "Window disabled":"Geen venster","Start hour":"Startuur","End hour":"Einduur",
    "Select at least one weekday":"Selecteer minstens één weekdag"},
  fr:{"Once":"Une fois","Daily":"Chaque jour","Specific days":"Jours spécifiques",
    "Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi","Thursday":"Jeudi",
    "Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche",
    "Allowed charging times":"Heures de recharge autorisées","Charging days":"Jours de recharge",
    "No day selected":"Jour non sélectionné","Window enabled":"Plage active",
    "Window disabled":"Aucune plage","Start hour":"Début","End hour":"Fin",
    "Select at least one weekday":"Sélectionnez au moins un jour"},
  de:{"Once":"Einmalig","Daily":"Täglich","Specific days":"Bestimmte Tage",
    "Allowed charging times":"Erlaubte Ladezeiten"},
  es:{"Once":"Una vez","Daily":"Diario","Specific days":"Días específicos",
    "Allowed charging times":"Horarios de carga permitidos"},
  da:{"Once":"Én gang","Daily":"Dagligt","Specific days":"Bestemte dage",
    "Allowed charging times":"Tilladte ladetider"},
  nb:{"Once":"Én gang","Daily":"Daglig","Specific days":"Bestemte dager",
    "Allowed charging times":"Tillatte ladetider"},
  sv:{"Once":"En gång","Daily":"Dagligen","Specific days":"Specifika dagar",
    "Allowed charging times":"Tillåtna laddtider"}
}))Object.assign(MC_TEXT[locale],terms);
const MC_MODES = ["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"];
const MC_STYLE = [
  ":host{display:block;color:var(--primary-text-color,#20252b);font:inherit}",
  ".root{background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e5e7eb);border-radius:14px;padding:20px;box-shadow:0 1px 4px #0000000b}",
  ".heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}",
  "h2{font-size:20px;font-weight:650;line-height:1.4;margin:0 0 8px}h3{font-size:15px;font-weight:600;margin:0}p{margin:5px 0;line-height:1.5}",
  ".muted{color:var(--secondary-text-color,#65717e)}.small{font-size:12px}.value{font-weight:700;font-size:22px}",
  ".tabs,.controls,.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.tabs{gap:3px;border-bottom:1px solid var(--divider-color,#e5e7eb);margin-bottom:20px}",
  "input,button,select,textarea,a.action{font:inherit;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px;padding:9px 11px;cursor:pointer;text-decoration:none;min-height:40px}.tabs button{border:0;border-bottom:3px solid transparent;border-radius:0;background:transparent;padding:10px 13px;color:var(--secondary-text-color,#667085)}",
  ".tabs button[aria-selected=true]{color:var(--primary-color,#1976d2);border-bottom-color:var(--primary-color,#1976d2);background:transparent;font-weight:650}button.active{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);border-color:var(--primary-color,#1976d2)}",
  "button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#1976d2);outline-offset:2px}",
  ".grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}",
  ".card{border:1px solid var(--divider-color,#e1e4e8);border-radius:10px;padding:14px;min-width:0;margin:8px 0}.settings-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:8px}.settings-card{margin:0;min-height:0}.settings-card.expanded{grid-column:1/-1}.schedule-days{gap:4px}.schedule-days button{min-width:0;padding:7px 9px}.settings-heading{min-width:0;flex:1}.settings-heading p{margin-top:5px}.settings-card .row{align-items:flex-start}.config-code{white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid var(--divider-color,#e1e4e8);border-radius:8px;background:var(--secondary-background-color,#f7f8fa);font-size:12px;line-height:1.5}",
  ".mc-icon{--mdc-icon-size:20px;display:inline-block;vertical-align:middle;margin-right:6px;flex:none;color:var(--primary-color,#1976d2)}.mc-icon.good{color:var(--success-color,#278355)}.mc-icon.warn{color:var(--warning-color,#b57418)}.mc-icon.bad{color:var(--error-color,#d43b38)}.mc-icon.quiet{color:var(--secondary-text-color,#65717e)}.mc-icon.solar{color:var(--warning-color,#b57418)}button .mc-icon{--mdc-icon-size:18px;color:inherit}.tabs .mc-icon{color:inherit}.metric .mc-icon{--mdc-icon-size:24px}.soc-track{height:8px;border-radius:6px;background:var(--divider-color,#ddd);overflow:hidden;margin:7px 0}.soc-fill{height:100%;background:var(--primary-color,#1976d2);border-radius:6px}.message[role=alert]{color:var(--error-color,#d43b38);white-space:pre-wrap;overflow-wrap:anywhere}",
  ".metric{background:var(--secondary-background-color,#f6f8fa);border:1px solid var(--divider-color,#e1e4e8);border-radius:8px;padding:10px;min-width:0}",
  ".row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}",
  ".details{margin-top:10px;padding-top:9px;border-top:1px solid var(--divider-color,#ddd)}.assignment-editor{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.assignment-editor p{flex-basis:100%}.assignment-editor select{width:100%;min-width:0;max-width:100%;box-sizing:border-box}",
  ".pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:5px 0}",
  ".field{display:flex;flex-direction:column;gap:4px;margin:8px 0}.field label{font-size:13px;color:var(--secondary-text-color,#65717e)}",
  ".field input,.field select{width:100%;box-sizing:border-box;padding:10px;border:1px solid var(--divider-color,#cfd6de);background:var(--card-background-color,#fff);color:inherit;border-radius:8px}.yaml-editor{margin:12px 0;padding:18px;border:1px solid var(--divider-color,#ccd4de);border-radius:10px;max-width:100%;box-sizing:border-box}.yaml-editor textarea{display:block;width:100%;box-sizing:border-box;min-height:340px;resize:vertical;font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;background:var(--secondary-background-color,#f7f8fa);margin-top:8px}.yaml-editor select{width:100%;max-width:100%;box-sizing:border-box}.yaml-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.yaml-editor pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}.yaml-error{border-left:3px solid var(--error-color,#bb3939);padding:8px 12px}.settings-toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;align-items:center}",
  ".message{font-size:13px;margin:9px 0}.pending{color:var(--warning-color,#b57418)}.confirmed{color:var(--success-color,#278355)}",
  ".notice{border:1px solid var(--divider-color,#e5e7eb);border-radius:8px;padding:11px 13px;background:var(--secondary-background-color,#f6f8fa);margin:12px 0;font-size:13px}",
  ".error{border-color:var(--error-color,#d43b38)}.chart{overflow-x:auto;width:100%}",
  ".legend{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--secondary-text-color,#65717e)}.legend-toggle{font-size:12px;border:0;padding:4px;min-height:30px;background:transparent;color:inherit}.legend-toggle[aria-pressed=false]{opacity:.5;text-decoration:line-through}",
  ".dot{display:inline-block;width:11px;height:11px;margin-right:5px;border-radius:2px}",
  ".plan-lane{margin:10px 0;border:1px solid var(--divider-color,#d8dde3);border-radius:11px;padding:11px}",
  ".object-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:10px;margin:9px 0;align-items:start}.object-grid>.card{margin:0;min-width:0}.object-grid>.expanded{grid-column:1/-1}.charger-state-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 12px;padding:8px 0}.charger-power{padding:8px 0;border-bottom:1px solid var(--divider-color,#ddd)}@media(min-width:800px){.charger-state-grid{grid-template-columns:repeat(auto-fit,minmax(105px,1fr))}}.setup-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:0 12px}.setup-fields .field{min-width:0}.setup-fields>p{grid-column:1/-1}.goal-track,.goal-ticks{box-sizing:border-box}.session-summary{margin:8px 0;padding:8px 0;border-top:1px solid var(--divider-color,#ddd)}.session-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:7px;margin:7px 0}",
  ".plan-lane svg{display:block;min-width:680px;width:100%;height:auto}",
  ".plan-lane .chart{margin-top:5px}",
  ".owner-inventory{margin-top:14px;border-top:1px solid var(--divider-color,#bbb);padding-top:12px}.owner-inventory>h4{font-size:15px;margin:0 0 9px}.owner-group{margin:7px 0 12px;padding:8px 10px;border:1px solid var(--divider-color,#ccc);border-radius:8px;min-width:0}.owner-group h4{font-size:13px;margin:0 0 8px}.owner-group .pair{word-break:break-word}.owner-configure{margin-top:8px}.owner-configure a{display:inline-block;margin-top:4px}.owner-hint{font-size:12px}.owner-inventory .row{flex-wrap:wrap}",
  ".combined-plan{margin:12px 0 18px}.combined-plan svg{display:block;width:100%;height:auto;min-width:0}.combined-plan .chart{overflow:hidden}.lane-summary{overflow-wrap:anywhere}.quick-goal{margin:10px 0;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:9px;background:var(--secondary-background-color,#f6f8fa)}.quick-goal h4{font-size:14px;margin:0 0 6px}.goal-controls{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(90px,1fr);gap:10px}.quick-goal button{margin-top:6px}.schedule-editor{margin:8px 0}.overview-actions{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px}.goal-timing{line-height:1.4}.financial-details{padding:4px 0}.object-disclosure:not([open])>:not(summary){display:none}",
  "@media(max-width:600px){.goal-controls{grid-template-columns:1fr}.quick-goal{padding:9px}.combined-plan svg text{font-size:10px}.plan-lane{padding:8px}}",
  ".vehicle-summary{margin:8px 0}.vehicle-target{display:flex;align-items:baseline;gap:6px}.vehicle-soc{font-size:26px;line-height:1.2}.vehicle-state{text-align:right}.vehicle-deadline{font-size:13px}.goal-outcome{border-top:1px solid var(--divider-color,#ddd);padding-top:6px;margin:6px 0}.goal-status{display:block;font-size:14px}.goal-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:6px 0}.goal-metric{display:flex;flex-direction:column;gap:2px;overflow-wrap:anywhere}.goal-metric strong{font-size:15px}.goal-track{position:relative;height:20px;margin:5px 3px 4px;background:var(--secondary-background-color,#eaecef);border-radius:5px}.goal-window{position:absolute;top:5px;bottom:5px;border-radius:3px;box-sizing:border-box}.goal-window.conditional{opacity:.65;border:1px dashed currentColor}.goal-deadline-marker{position:absolute;top:-3px;bottom:-3px;border-left:2px dashed var(--primary-text-color,#222)}.goal-ticks{position:relative;height:17px;font-size:10px;display:block}.goal-ticks>span{position:absolute;white-space:nowrap}.schedule-days button{border-radius:20px;flex:1}.schedule-modes{gap:4px}.schedule-modes button{flex:1;min-width:0;padding:7px}.schedule-actions{justify-content:space-between}.schedule-time .field{display:flex;flex-direction:row;justify-content:space-between;align-items:center}.schedule-time input{width:auto;max-width:100%;min-width:0}.goal-timeline{margin:9px 0}",
  ".plan-key{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:6px 0;font-size:12px}",
  ".plan-swatch{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:4px}",
  ".operational-indicator{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:500;white-space:nowrap}.operational-indicator:before{content:'';width:8px;height:8px;flex:none;border-radius:50%;background:var(--secondary-text-color,#858585)}.operational-indicator.charging:before{background:var(--success-color,#25833b)}.operational-indicator.problem:before{background:var(--error-color,#c62828)}.operational-indicator.ready:before{background:var(--success-color,#25833b)}.operational-indicator.problem{white-space:normal;text-align:right}",
  ".plan-caution{font-size:12px;color:var(--secondary-text-color,#65717e);line-height:1.5}",
  "svg{width:100%;min-width:440px;height:220px}svg text{fill:var(--secondary-text-color,#65717e);font-size:11px}",
  "@media(max-width:600px){.root{padding:12px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.metric{padding:10px}.metric .value{font-size:18px;overflow-wrap:anywhere}.tabs{display:flex;overflow-x:auto;flex-wrap:nowrap}.tabs button{font-size:12px;padding:9px 10px;white-space:nowrap;flex-shrink:0}.settings-grid{grid-template-columns:1fr}}",
  // Calm dense object-first D0/D1 cards; D3/D4 properties are native
  // keyboard-accessible foldable rows, never a simultaneous 82-field form.
  ".object-card{margin:9px 0;padding:14px 16px;border-radius:12px;box-shadow:0 1px 2px #00000009}.object-card>.row:first-child{padding-bottom:7px;border-bottom:1px solid var(--divider-color,#e5e7eb)}.object-card h3{font-size:15px;letter-spacing:-.01em}.object-card>.pair{padding:4px 0}.object-card .plan-key{margin:7px 0}",
  ".object-card .controls{margin:10px 0 4px}.object-card .quick-goal{margin:10px 0;background:transparent}.object-card .details{margin-top:14px}.object-card>.small{color:var(--secondary-text-color,#667085)}",
  ".owner-inventory{margin:16px 0 0;border-top:1px solid var(--divider-color,#d9dce2);padding:12px 0 0}.owner-inventory>h4{font-size:14px;margin:0 0 8px}.owner-group{margin:6px 0;padding:0;overflow:hidden;border-radius:9px;background:var(--card-background-color,#fff)}",
  ".owner-group>summary{cursor:pointer;padding:11px 12px;font-size:13px;font-weight:600;display:list-item;list-style-position:inside;user-select:none}.owner-group>summary:hover{background:var(--secondary-background-color,#f6f8fa)}.owner-group[open]>summary{border-bottom:1px solid var(--divider-color,#e1e4e8)}.owner-summary-count{font-size:11px;font-weight:400;color:var(--secondary-text-color,#65717e);margin-left:7px}",
  ".owner-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr));gap:0 16px;padding:3px 12px 8px}.owner-field{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;min-width:0;padding:7px 0;border-bottom:1px solid var(--divider-color,#e1e4e8)}.owner-field:last-child{border-bottom:0}.owner-field-info{flex:1;min-width:0;overflow-wrap:anywhere}.owner-field-label{font-size:11px;color:var(--secondary-text-color,#65717e);line-height:1.35}.owner-field-value{font-size:12px;font-weight:550;line-height:1.35;margin-top:3px;overflow-wrap:anywhere}.owner-field button{min-height:27px;padding:3px 8px;font-size:11px;border-radius:6px;white-space:nowrap;background:transparent}",
  ".owner-inventory>.owner-configure{margin-top:10px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}.owner-inventory>.owner-configure p{flex-basis:100%}.owner-inventory>button{margin:8px 0;min-height:34px}",
  "@media(max-width:600px){.object-card{padding:11px}.owner-fields{grid-template-columns:1fr}.owner-group>summary{padding:12px 9px}.pair{grid-template-columns:minmax(0,42%) minmax(0,58%);gap:9px}}",
  ".quick-assignment{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:9px 0}.quick-assignment label{font-weight:600;font-size:13px}.quick-vehicle-select{flex:1;min-width:155px;max-width:360px;min-height:38px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#1f2937);border:1px solid var(--divider-color,#d6dce4);border-radius:8px;padding:6px 12px;cursor:pointer}.quick-vehicle-select:disabled{opacity:.65;cursor:default}",
  ".quick-owner-panel{margin:12px 0}.quick-owner-line{display:grid;grid-template-columns:minmax(140px,1fr) minmax(210px,2fr) minmax(110px,1fr);align-items:center;gap:16px;padding:7px 0;border-bottom:1px solid var(--divider-color,#e7e9ed)}.quick-owner-line:last-child{border-bottom:0}.quick-owner-line .quick-assignment{margin:0;padding:3px 0}.quick-owner-line .quick-assignment label{display:none}.mc-apex{position:relative;isolation:isolate;min-height:165px;max-width:100%;overflow:hidden}.mc-apex svg{min-width:0!important}.mc-apex .apexcharts-legend{position:absolute;max-width:100%;overflow:hidden}.combined-plan .mc-apex{min-height:290px}",
  "@media(max-width:650px){.quick-owner-line{grid-template-columns:1fr;gap:3px}.quick-owner-line .quick-vehicle-select{max-width:none}.quick-assignment{align-items:flex-start}.quick-assignment label{flex:0 0 100%}}"
].join("");

function mcEl(tag, css, text) {
  const node = document.createElement(tag);
  if (css) node.className = css;
  if (text !== undefined && text !== null) node.textContent = mcTr(text);
  return node;
}
const MC_ICONS={
  "Overview":"view-dashboard-outline","Charging Plan":"calendar-clock","Charging plan":"calendar-clock",
  "Chargeable Assets":"car-electric-outline","Chargers":"ev-station","Settings":"cog-outline",
  "Refresh":"refresh","Automatic":"auto-fix","Solar":"solar-power","Economy":"cash","Ready By":"clock-check-outline",
  "Force Charge":"lightning-bolt","Off":"power","Save":"content-save-outline","Cancel":"close",
  "Edit YAML":"code-json","Close YAML editor":"close","Edit":"pencil-outline",
  "Stop charging":"stop-circle-outline","Start charging":"play-circle-outline","Pause charging":"pause-circle-outline",
  "Resume charging":"play-circle-outline","Schedule charging":"calendar-clock","Set charging goal":"target",
  "Save charging goal":"content-save-outline","Add asset":"plus","Add charger":"plus",
  "Active chargers":"ev-station","Actual power":"lightning-bolt","Effective charging power":"lightning-bolt",
  "Current price":"currency-eur","Spot price":"currency-eur","Variable reference price":"currency-eur",
  "Solar production":"solar-power","Solar surplus":"white-balance-sunny","Home consumption":"home-lightning-bolt-outline",
  "Grid power":"transmission-tower","Battery":"battery-outline","Target":"target","Connection":"connection",
  "Charger":"ev-station","Active session":"clock-outline","Measured session energy":"flash",
  "Charging site":"home-outline","Sources & bindings":"link-variant","Charging strategy":"tune-variant",
  "Safety & limits":"shield-check-outline","Integrations":"puzzle-outline"
};
function mcIconLabel(node, text, icon, tone=""){
  if(!icon)return node;
  const el=mcEl("ha-icon","mc-icon"+(tone?" "+tone:""));
  el.setAttribute("icon","mdi:"+icon);
  el.setAttribute("aria-hidden","true");
  node.textContent=mcTr(text);
  if(typeof node.prepend==="function")node.prepend(el);
  else node.append(el);
  return node;
}
function mcIconFor(text){
  if(MC_ICONS[text])return MC_ICONS[text];
  return Object.entries(MC_ICONS).find(([key])=>mcTr(key)===text)?.[1];
}
function mcAssetIcon(a){
  return a.temporary?"account-clock-outline":({car:"car-electric-outline",bicycle:"bicycle",
    motorcycle:"motorbike",scooter:"scooter-electric",other:"battery-outline"}[a.kind]||"battery-outline");
}
function mcSocBar(container,observation,color){
  if(observation?.quality!=="ok"||typeof observation.value!=="number"||
      !Number.isFinite(observation.value)||observation.value<0||observation.value>100)return;
  const track=mcEl("div","soc-track");track.setAttribute("role","progressbar");
  track.setAttribute("aria-label",mcTr("Battery"));track.setAttribute("aria-valuemin","0");
  track.setAttribute("aria-valuemax","100");track.setAttribute("aria-valuenow",String(observation.value));
  const fill=mcEl("div","soc-fill");fill.style.width=observation.value+"%";if(color)fill.style.background=color;track.append(fill);container.append(track);
}
function mcButton(text, action, css) {
  const node = mcEl("button", css || "", text);
  node.type = "button";
  node.addEventListener("click", action);
  return mcIconLabel(node,text,mcIconFor(text));
}
function mcValue(observation, suffix) {
  if (!observation || observation.quality !== "ok" || observation.value === null || observation.value === undefined) return mcTr("Unknown");
  if (typeof observation.value === "boolean") return mcTr(observation.value ? "Connected" : "Disconnected");
  return String(observation.value) + (suffix || "");
}
function mcTime(value, zone) {
  if (!value) return mcTr("Not set");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? mcTr("Unknown") : date.toLocaleString(undefined, {timeZone: zone || "UTC", month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function mcPair(target, left, right) {
  const pair=mcEl("div","pair");
  pair.append(mcIconLabel(mcEl("span","muted",left),left,mcIconFor(left)),mcEl("span","",right));
  target.append(pair);
}
function mcSVG(tag, attrs, text) {
  const node=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for (const [name,value] of Object.entries(attrs||{})) node.setAttribute(name,String(value));
  if(text!==undefined)node.textContent=mcTr(text);
  return node;
}


function mcPlanName(slot,configuration,labels){
  const charger=(configuration.chargers||[]).find(c=>c.id===slot.charger_id);
  const asset=(configuration.assets||[]).find(a=>a.id===slot.asset_id);
  const car=asset?asset.name:(slot.asset_id||"Unidentified");
  const station=charger?charger.name:(slot.charger_id||"Unknown charger");
  return labels==="vehicle"?car:labels==="charger"?station:car+" · "+station;
}

// One Basic-style power/price overview above the existing per-Charger lanes.
// Never invent unavailable meter samples, convert a quote to a bill, or
// attribute anonymous historical power to today's selected vehicle.
// One local immutable MIT library shared by the native panel and card.
// The browser must never fetch a third-party CDN or masquerade SVG as Apex.
let mcApexLibrary=null;
function mcEnsureApex(){
  if(typeof window!=="undefined"&&typeof window.ApexCharts==="function")
    return Promise.resolve(window.ApexCharts);
  if(mcApexLibrary)return mcApexLibrary;
  mcApexLibrary=new Promise((resolve,reject)=>{
    if(typeof document==="undefined"||!document.head){
      reject(Error("Local ApexCharts requires a real browser"));return;
    }
    const existing=document.querySelector?.('script[data-multicharge-apex]');
    if(existing){
      existing.addEventListener("load",()=>resolve(window.ApexCharts),{once:true});
      existing.addEventListener("error",()=>reject(Error("Local ApexCharts unavailable")),{once:true});
      return;
    }
    const node=document.createElement("script");
    node.async=true;
    node.src="/robotix_multicharge/frontend/vendor/apexcharts.min.js";
    node.dataset.multichargeApex="3.49.1";
    node.addEventListener("load",()=>{
      if(typeof window.ApexCharts==="function")resolve(window.ApexCharts);
      else reject(Error("Bundled ApexCharts did not initialize"));
    },{once:true});
    node.addEventListener("error",()=>reject(Error("Bundled ApexCharts unavailable")),{once:true});
    document.head.append(node);
  }).catch(error=>{mcApexLibrary=null;throw error;});
  return mcApexLibrary;
}
// Align the *rendered* time axes, not just their timestamp ranges. The
// right-hand price axis, labels and responsive card padding consume different
// amounts of space. Reuse Apex's actual grid geometry and its native padding.
function mcPlotBounds(plot){
  const lines=[...plot.querySelectorAll(".apexcharts-gridline")];
  const horizontal=lines.map(el=>el.getBoundingClientRect())
    .filter(r=>r.width>20&&r.height<3).sort((a,b)=>b.width-a.width)[0];
  if(horizontal)return {left:horizontal.left,right:horizontal.right};
  return null;
}
function mcSchedulePlanAlignment(root){
  if(!root?.querySelectorAll||typeof window==="undefined")return;
  if(root._mcAlignBusy){root._mcAlignPending=true;return;}
  if(root._mcAlignTimer!=null)return;
  root._mcAlignTimer=setTimeout(async()=>{
    root._mcAlignTimer=null;root._mcAlignBusy=true;
    try{
      for(let pass=0;pass<4;pass++){
        const plots=[...root.querySelectorAll(".mc-apex")];
        if(!plots.length||plots.some(p=>!p._mcApex||!mcPlotBounds(p)))return;
        const bounds=plots.map(p=>({p,...mcPlotBounds(p)}));
        // Recover natural grid edges before our additional padding. This
        // allows axes to expand again after resizing or changing series.
        const left=Math.max(...bounds.map(b=>b.left-(b.p._mcExtraLeft||0)));
        const right=Math.min(...bounds.map(b=>b.right+(b.p._mcExtraRight||0)));
        if(right-left<40)return;
        const updates=[];
        for(const b of bounds){
          const l=Math.max(0,Math.round(left-(b.left-(b.p._mcExtraLeft||0))));
          const r=Math.max(0,Math.round((b.right+(b.p._mcExtraRight||0))-right));
          if(Math.abs(l-(b.p._mcExtraLeft||0))<=1&&Math.abs(r-(b.p._mcExtraRight||0))<=1)continue;
          b.p._mcExtraLeft=l;b.p._mcExtraRight=r;
          updates.push(b.p._mcApex.updateOptions({grid:{padding:{left:3+l,right:8+r}}},false,false,false));
        }
        if(updates.length)await Promise.all(updates);
        else break;
      }
      const bounds=[...root.querySelectorAll(".mc-apex")].map(mcPlotBounds).filter(Boolean);
      if(!bounds.length)return;
      const left=Math.max(...bounds.map(b=>b.left)),right=Math.min(...bounds.map(b=>b.right));
      for(const block of root.querySelectorAll(".goal-timeline")){
        const box=block.getBoundingClientRect();
        for(const el of block.querySelectorAll(".goal-track,.goal-ticks")){
          el.style.marginLeft=Math.max(0,left-box.left)+"px";
          el.style.marginRight=Math.max(0,box.right-right)+"px";
        }
      }
    }catch(error){
      // Chart rendering stays usable; a failed alignment is not hidden from
      // browser acceptance (which compares actual geometry).
      console.warn("MultiCharge plot alignment",error);
    }finally{
      root._mcAlignBusy=false;
      if(root._mcAlignPending){root._mcAlignPending=false;mcSchedulePlanAlignment(root);}
    }
  },0);
}
function mcMountApex(plot,options){
  plot.className+=" mc-apex";
  plot.setAttribute("role","img");
  plot.setAttribute("aria-label",options.chart?.id||"MultiCharge power timeline");
  plot.setAttribute("data-chart-engine","apexcharts-3.49.1");
  plot.setAttribute("data-range-start",String(options.xaxis.min));
  plot.setAttribute("data-range-end",String(options.xaxis.max));
  plot._mcSignature=JSON.stringify(options, (key,value)=>typeof value==="function"?String(value):value);
  const key=mcEl("div","legend");
  for(const [i,series] of (options.series||[]).entries()){
    if(!series.data?.length)continue;
    const label=mcEl("button","legend-toggle");label.setAttribute("aria-pressed","true");
    label.addEventListener("click",()=>{if(!plot._mcApex)return;plot._mcApex.toggleSeries(series.name);const visible=label.getAttribute("aria-pressed")!=="true";label.setAttribute("aria-pressed",String(visible));});
    const dot=mcEl("span","dot");dot.style.background=options.colors[i];
    label.append(dot,mcEl("span","",series.name));key.append(label);
  }
  plot._mcLegend=key;
  // Node-only DOM checks cannot assert that a browser rendered a graph:
  // real Chromium tests below inspect the Apex-generated SVG and tooltips.
  if(typeof window==="undefined"||typeof document==="undefined"||!document.head)
    return;
  void mcEnsureApex().then(Chart=>{
    if(plot.isConnected===false)return;
    options.chart.events={...options.chart.events,
      mounted:()=>mcSchedulePlanAlignment(plot.getRootNode()),
      updated:()=>mcSchedulePlanAlignment(plot.getRootNode())};
    const chart=new Chart(plot,options);
    plot._mcApex=chart;
    return chart.render().then(()=>mcSchedulePlanAlignment(plot.getRootNode())).catch(error=>{
      chart.destroy();plot._mcApex=null;
      plot.append(mcEl("p","plan-caution","ApexCharts render failed: "+String(error?.stack||error?.message||error).slice(0,650)));
    });
  }).catch(error=>{
    if(plot.isConnected!==false)
      plot.append(mcEl("p","plan-caution","ApexCharts unavailable: "+String(error?.message||error)));
  });
}
function mcApexCommon(from,until,height,title,withPrice=false){
  const colors=["#7890aa","#478ab8","#18856d","#b78330"];
  return {
    chart:{id:title,type:"line",height,background:"transparent",
      fontFamily:"inherit",foreColor:"#687784",parentHeightOffset:0,
      animations:{enabled:false},toolbar:{show:true,tools:{
        download:true,selection:false,zoom:true,zoomin:true,zoomout:true,pan:false,reset:true
      }},zoom:{enabled:true,autoScaleYaxis:false},
      // Keep the same source/time truth across panels and stacked Lovelace cards.
      redrawOnParentResize:true,redrawOnWindowResize:true},
    theme:{mode:(typeof window!=="undefined"&&
      window.matchMedia?.("(prefers-color-scheme: dark)")?.matches)?"dark":"light"},
    colors,
    stroke:{curve:"straight",width:[2,2,2.8,1.8],dashArray:[5,2,0,5]},
    fill:{type:"solid",opacity:1},
    dataLabels:{enabled:false},
    markers:{size:0,hover:{size:5}},
    grid:{strokeDashArray:3,borderColor:"#8b97a62b",padding:{left:3,right:8}},
    xaxis:{type:"datetime",min:from,max:until,labels:{datetimeUTC:false},
      axisBorder:{show:false},axisTicks:{show:false}},
    yaxis:[{
      // Apex 3.49 uses the *visible* nonempty series count for its y-axis
      // matching. Explicitly group the three power series so adding a
      // separate price axis cannot index an absent series on sparse days.
      ...(withPrice?{seriesName:["Proposed","Accepted","Measured"]}:{}),
      title:{text:"Measured / proposed / accepted · kW"},
      min:0,decimalsInFloat:2,
      labels:{formatter:v=>Number(v).toFixed(1)}
    },...(withPrice?[{
      opposite:true,seriesName:"Reference price (EUR/kWh)",
      title:{text:"Price · EUR/kWh"},decimalsInFloat:4,
      labels:{formatter:v=>Number(v).toFixed(3)}
    }]:[])],
    tooltip:{shared:true,intersect:false,x:{format:"dd MMM HH:mm"},
      y:{formatter:(v,{seriesIndex})=>v===null||v===undefined?"Not measured":
        (withPrice&&seriesIndex===3?Number(v).toFixed(4)+" EUR/kWh":
          Number(v).toFixed(2)+" kW")}},
    legend:{show:false},
    noData:{text:"No qualified measurements / schedule for this period"}
  };
}
// Shared interval projection for both chart levels. Endpoints keep a single
// quarter visible; null breaks separate genuinely missing intervals.
function mcPlanOwnerColor(data,assetId,chargerId){
  const config=data.configuration||{};
  const byCharger=config.controller?.plan_color_by==="charger";
  const color=mcOwnerColor(byCharger?"charger":"asset",byCharger?chargerId:assetId,
    config,data.plan_palette);
  return color.startsWith("var(")?"#757d87":color;
}
function mcPlanTickText(value,data){
  return new Date(Number(value)).toLocaleString(undefined,{
    timeZone:data.timezone||"UTC",day:"numeric",hour:"2-digit",minute:"2-digit",hourCycle:"h23"
  });
}
function mcPlanSeries(data,visibleChargers,rows,actuals,forecast,includeTotals=false){
  const from=Date.parse(data.start),until=Date.parse(data.end);
  const visible=new Set(visibleChargers.map(c=>c.id));
  const config=data.configuration||{};
  const labels=config.controller?.plan_label_mode||"both";
  const groups=new Map();
  for(const [source,key,status,index] of [
    [rows,"proposed_power_kw","Proposed",0],
    [rows,"accepted_power_kw","Accepted",1],
    [actuals,"actual_power_kw","Measured",2],
    [forecast,"indicative_power_kw","Indicative · not reserved",3]
  ]){
    for(const row of source){
      if(!visible.has(row.charger_id)||typeof row[key]!=="number"||
          !Number.isFinite(row[key])||row[key]<0)continue;
      const a=Date.parse(row.start),b=Date.parse(row.end);
      if(!Number.isFinite(a)||!Number.isFinite(b)||b<=a||b<=from||a>=until)continue;
      const assetId=index===2&&row.asset_provenance!=="confirmed_closed_session"?null:row.asset_id;
      const color=mcPlanOwnerColor(data,assetId,row.charger_id);
      const label=mcPlanName({...row,asset_id:assetId},config,labels);
      const id=JSON.stringify([index,row.charger_id,assetId]);
      if(!groups.has(id))groups.set(id,{name:status+" · "+label,color,index,chargerId:row.charger_id,intervals:new Map()});
      const g=groups.get(id);
      const x=Math.max(a,from),y=Math.min(b,until);
      if(!g.intervals.has(x))g.intervals.set(x,{start:x,end:y,power:row[key]});
    }
  }
  const ownerGroups=[...groups.values()];
  // Preserve aggregate known site power for simultaneous qualified loads.
  // Never total independent conditional alternatives or mix plan and actual.
  if(includeTotals)for(const [index,status] of [[0,"Proposed"],[1,"Accepted"],[2,"Measured"]]){
    const totals=new Map(),events=new Map(),active=new Map();
    for(const g of ownerGroups.filter(x=>x.index===index)){
      for(const q of g.intervals.values()){
        for(const [stamp,add] of [[q.start,true],[q.end,false]]){
          if(!events.has(stamp))events.set(stamp,[]);
          events.get(stamp).push({id:g.chargerId,add,q});
        }
      }
    }
    const boundaries=[...events.keys()].sort((a,b)=>a-b);
    for(let i=0;i<boundaries.length-1;i++){
      const stamp=boundaries[i],batch=events.get(stamp);
      for(const event of batch.filter(e=>!e.add)){
        const rows=active.get(event.id);
        rows?.delete(event.q);
        if(!rows?.size)active.delete(event.id);
      }
      for(const event of batch.filter(e=>e.add)){
        if(!active.has(event.id))active.set(event.id,new Set());
        active.get(event.id).add(event.q);
      }
      const total={start:stamp,end:boundaries[i+1],power:0,owners:new Set()};
      for(const [id,rows] of active){
        if(rows.size!==1)continue; // ambiguous overlap is not additional power
        total.power+=[...rows][0].power;total.owners.add(id);
      }
      if(total.owners.size)totals.set(stamp,total);
    }
    if([...totals.values()].some(q=>q.owners.size>1))
      ownerGroups.push({name:status+" · known site total",index:5,color:"#697582",intervals:totals});
  }
  const usedNames=new Set();
  return ownerGroups.map(g=>{
    const intervals=[...g.intervals.values()].sort((a,b)=>a.start-b.start);
    const points=[];
    for(let i=0;i<intervals.length;i++){
      const q=intervals[i];
      points.push({x:q.start,y:q.power},{x:q.end-1,y:q.power});
      if(intervals[i+1]?.start!==q.end)points.push({x:q.end,y:null});
    }
    const name=usedNames.has(g.name)?g.name+" · "+(config.chargers||[]).find(c=>c.id===g.chargerId)?.name:g.name;
    usedNames.add(name);
    return {name,data:points,type:[0,2,3].includes(g.index)?"area":"line",
      color:g.color,index:g.index};
  });
}
function mcPlanChartOptions(data,series,height,title,price=null){
  const from=Date.parse(data.start),until=Date.parse(data.end);
  const options=mcApexCommon(from,until,height,title,!!price);
  options.series=[...series,...(price?[price]:[])].map(({name,data,type})=>({name,data,type}));
  const all=[...series,...(price?[price]:[])];
  options.colors=all.map(s=>s.color);
  options.stroke={curve:"stepline",width:all.map(s=>[2,2.5,2.5,2,1.8,1.8][s.index]),
    dashArray:all.map(s=>[0,0,0,5,0,2][s.index])};
  options.fill={type:"solid",opacity:all.map(s=>[.32,1,.72,.15,1,1][s.index])};
  // The view range selector is the sole zoom control; separate chart zoom
  // would misalign otherwise identical time axes and charging-window bars.
  options.chart.zoom={enabled:false};
  Object.assign(options.chart.toolbar.tools,{zoom:false,zoomin:false,zoomout:false,reset:false});
  options.xaxis={...options.xaxis,type:"numeric",tickAmount:4,decimalsInFloat:0,
    labels:{formatter:value=>mcPlanTickText(value,data)}};
  options.tooltip.x={formatter:value=>mcPlanTickText(value,data)};
  options.yaxis[0].title.text="";
  // Units are already visible in chart headings, legend and hover readback.
  // Avoid a second vertical title stealing scarce mobile plot width.
  if(price){
    options.yaxis[0].seriesName=series.map(s=>s.name);
    options.yaxis[1].seriesName=price.name;
    options.yaxis[1].title.text="";
    if(!series.length)options.yaxis=[options.yaxis[1]];
  }
  options.tooltip.shared=false;options.tooltip.intersect=false;
  options.tooltip.y.formatter=(v,{seriesIndex})=>v===null||v===undefined?"Not measured":
    Number(v).toFixed(all[seriesIndex]?.index===4?4:2)+
      (all[seriesIndex]?.index===4?" "+price.currency+"/kWh":" kW");
  options.annotations={xaxis:Date.now()>=from&&Date.now()<until?
    [{x:Math.floor(Date.now()/60000)*60000,borderColor:"#b86a44",label:{text:"Now"}}]:[]};
  return options;
}
function mcApexLane(data,charger,rows,actuals,forecast){
  const plot=mcEl("div","chart");
  const series=mcPlanSeries(data,[charger],rows,actuals,forecast);
  if(!series.length){
    plot.append(mcEl("p","muted small",mcTr("No qualified physical or planned power in this period")));
    return plot;
  }
  mcMountApex(plot,mcPlanChartOptions(data,series,190,"Charger "+charger.id));
  const lane=mcEl("div");lane.append(plot);if(plot._mcLegend)lane.append(plot._mcLegend);return lane;
}
function mcCombinedChargingChart(data, visibleChargers, slots, actuals, forecast=[]){
  const wrapper=mcEl("section","card combined-plan");
  wrapper.append(mcEl("h3","",mcTr("All charging · Power & price")));
  wrapper.append(mcEl("p","muted small",
    mcTr("Measured physical · accepted · proposed · independently scaled price")));
  const from=Date.parse(data.start),until=Date.parse(data.end);
  if(!Number.isFinite(from)||!Number.isFinite(until)||until<=from){
    wrapper.append(mcEl("p","muted",mcTr("No qualified timeline")));return wrapper;
  }
  const count=Math.ceil((until-from)/900000);
  if(count>200||count<1){wrapper.append(mcEl("p","muted",mcTr("Unavailable")));return wrapper;}
  const visible=new Set(visibleChargers.map(c=>c.id));
  const buckets=Array.from({length:count},(_,i)=>({at:from+i*900000,price:null}));
  const series=mcPlanSeries(data,visibleChargers,slots,actuals,forecast,true);
  const quotes=(data.price_slots||[]).filter(x=>
    typeof x.price_per_kwh==="number"&&Number.isFinite(x.price_per_kwh)&&
    /^[A-Z]{3}$/.test(x.currency||""));
  const currency=[...new Set(quotes.map(x=>x.currency))];
  const basis=[...new Set(quotes.map(x=>x.basis||"unqualified"))];
  const priceReady=currency.length===1&&basis.length===1;
  if(priceReady)for(const item of buckets){
    const matched=quotes.filter(q=>Date.parse(q.start)<=item.at&&
      Date.parse(q.end)>=item.at+900000);
    if(matched.length===1)item.price=matched[0].price_per_kwh;
  }
  const validPrice=priceReady&&buckets.some(x=>x.price!==null);
  const price=validPrice?{name:"Reference price ("+currency[0]+"/kWh)",index:4,
    color:"#626c7d",type:"line",currency:currency[0],
    data:buckets.flatMap(q=>[{x:q.at,y:q.price},{x:Math.min(q.at+900000,until)-1,y:q.price}])}:null;
  const plot=mcEl("div","chart");
  if(series.length||price)mcMountApex(plot,mcPlanChartOptions(data,series,310,
    "MultiCharge combined power and price",price));
  else plot.append(mcEl("p","muted small",
    mcTr("No qualified physical or planned power in this period")));
  wrapper.append(plot);if(plot._mcLegend)wrapper.append(plot._mcLegend);
  if(validPrice)wrapper.append(mcEl("p","muted small",
    basis[0]+" · "+currency[0]+"/kWh · "+mcTr("reference price, not an invoice")));
  if(!validPrice)wrapper.append(mcEl("p","muted small",
    mcTr("Price unavailable · no price series is fabricated")));
  else if(buckets.some(q=>q.price===null))
    wrapper.append(mcEl("p","muted small",
      mcTr("Price intervals incomplete; missing periods are not zero")));
  const future=slots.filter(s=>visible.has(s.charger_id)&&
    Date.parse(s.start)>=Date.now()&&Number.isFinite(s.proposed_power_kw)&&
    s.proposed_power_kw>=0);
  if(future.length){
    const kwh=future.reduce((sum,row)=>sum+
      (Number.isFinite(row.proposed_energy_kwh)?
       row.proposed_energy_kwh:row.proposed_power_kw/4),0);
    wrapper.append(mcEl("p","small",mcTr("Still planned")+" · "+
      kwh.toFixed(2)+" kWh · "+
      new Set(future.map(x=>x.charger_id)).size+" "+
      mcTr("chargers")));
  }

  return wrapper;
}

const MC_OWNER_UX_LOCALES = {
  nl:{
    "Complete object settings & sources":"Alle instellingen en bronnen van dit object",
    "Identity & strategy":"Identiteit en laadstrategie",
    "Energy & tariff sources":"Energie- en tariefbronnen",
    "Vehicle identity & lifetime":"Voertuigidentiteit en geldigheid",
    "Goal & timing":"Laaddoel en tijdstip",
    "Price & charging decisions":"Prijs- en laadvoorkeuren",
    "Battery & source references":"Batterij- en broninstellingen",
    "Identity & ownership":"Identiteit en eigenaarschap",
    "Connection & meter sources":"Verbindingen en meetbronnen",
    "Electrical hardware & circuit":"Elektrische aansluiting en stroomkring",
    "Additional owner settings":"Overige objectinstellingen",
    "Read from Home Assistant configuration":"Afkomstig uit Home Assistant-configuratie",
    "configured fields":"ingestelde velden",
    "Missing values are not assumed":"Ontbrekende waarden worden niet ingevuld",
    "Not configured":"Niet ingesteld","Yes":"Ja","No":"Nee",
    "Original vehicle at session time":"Voertuig tijdens de laadsessie",
    "Anonymous charger-only session":"Anonieme laadpaalsessie",
    "Physical STOP confirmed":"Fysieke STOP bevestigd",
    "Session stop reason":"Reden einde laadsessie",
    "Active session goal":"Doel van actieve sessie",
    "Indicative budget used":"Indicatief verbruikt budget",
    "Budget measurement quality":"Kwaliteit budgetmeting",
    "Charger at session time":"Laadpaal tijdens de sessie",
    "Vehicle charging history":"Laadgeschiedenis voertuig",
    "No confirmed charging history":"Geen bevestigde laadgeschiedenis",
    "Completed":"Afgerond",
    "Physical control owner":"Fysieke bediening door",
    "Physically commissioned":"Fysiek in gebruik genomen",
    "External control (monitor only)":"Externe sturing (alleen bewaking)",
    "Physical Charger & verified sources":"Fysieke laadpaal en geverifieerde bronnen",
    "Site energy configuration":"Energie-instellingen van de locatie",
    "Solar source type":"Type zonnebron",
    "Grid meter direction":"Richting netmeter",
    "Solar source type (native)":"Type zonnebron instellen",
    "Grid meter direction (native)":"Richting netmeter instellen",
    "Select the required native meter before enabling this Solar mode":"Selecteer eerst de vereiste echte meter voor deze zonnemodus",
    "Qualified Solar intervals":"Geverifieerde zonne-intervalwaarden",
    "Measured grid export":"Gemeten netinjectie",
    "Measured solar surplus":"Gemeten zonne-overschot",
    "Import is positive":"Afname is positief",
    "Export is positive":"Injectie is positief",
    "Phase and wiring settings are changed through the native Controller options after physical verification":"Fase- en aansluitinstellingen pas je aan via Controller-opties na fysieke verificatie",
    "Site controller ID":"Identiteit laadcontroller",
    "Hardware source bindings and commissioning use the native Charger options":"Hardwarebronnen en inbedrijfstelling via de laadpaalopties",
    "Vehicle source mappings use the native Vehicle options":"Voertuigbronnen via de voertuigopties",
    "Site source configuration uses the native Controller/Energy options":"Energiebronnen via Controller/Energie-opties",
    "Object ID":"Object-ID","Name":"Naam","Type":"Type",
    "Assigned vehicle":"Toegewezen voertuig",
    "Simultaneous chargers":"Gelijktijdige laadpalen",
    "Site power ceiling":"Vermogenslimiet locatie",
    "Maximum per-phase current":"Maximumstroom per fase",
    "Plan labels":"Planlabels",
    "Colors represent":"Kleuren volgens",
    "Show unreserved forecast":"Niet-gereserveerde prognose tonen",
    "Future tariff interval source":"Bron toekomstige tarieven",
    "Current import price source":"Bron actuele afnameprijs",
    "Current export price source":"Bron actuele injectieprijs",
    "Solar interval source":"Bron zonne-intervalwaarden",
    "Solar strategy":"Zonnestrategie",
    "Solar production sensor":"Sensor zonneproductie",
    "Available solar surplus sensor":"Sensor beschikbaar zonne-overschot",
    "Home consumption sensor":"Sensor huisverbruik",
    "Grid import/export sensor":"Sensor netafname/injectie",
    "Grid sensor sign":"Tekenconventie netmeter",
    "Site capacity meter":"Meter locatievermogen",
    "Power envelope source":"Bron beschikbaar vermogensbereik",
    "Temporary guest":"Tijdelijke gast",
    "Guest expires":"Gast vervalt",
    "Timeline color":"Kleur laadplanning",
    "Battery target":"Doel batterijpercentage",
    "Extra energy goal":"Doel extra energie",
    "Charging duration goal":"Doel laadduur",
    "Indicative budget goal":"Indicatief laadbudget",
    "Budget currency":"Budgetvaluta",
    "One-time Ready By":"Eenmalig klaar om",
    "Ready By frequency":"Herhaling klaar-om",
    "Specific weekday Ready By times":"Klaartijden per weekdag",
    "Allowed charging time windows":"Toegestane laadvensters",
    "Earliest charging start":"Vroegste laadstart",
    "Expected connection time":"Verwachte aansluiting",
    "Require continuous charging":"Aaneengesloten laden verplicht",
    "Minimum battery priority":"Minimaal batterijpercentage",
    "Early low-battery trigger":"Start bij lage batterijstand",
    "Maximum price per kWh":"Maximumprijs per kWh",
    "Tariff currency":"Tariefvaluta",
    "Immediate low-price trigger":"Direct starten bij lage prijs",
    "Opportunistic strategy":"Opportunistische strategie",
    "Vehicle charging priority":"Laadprioriteit voertuig",
    "Battery SoC sensor":"Sensor batterijpercentage",
    "Battery freshness sensor":"Sensor actualiteit batterij",
    "Vehicle-native command":"Voertuigcommando",
    "Vehicle-native current setting":"Stroominstelling voertuig",
    "Usable battery capacity":"Bruikbare batterijcapaciteit",
    "Vehicle charging limit":"Laadlimiet voertuig",
    "Charging efficiency":"Laadrendement",
    "Physical command owner":"Eigenaar fysieke bediening",
    "Physical commissioning":"Fysieke inbedrijfstelling",
    "Native Charger control switch":"Schakelaar fysieke laadpaal",
    "Cable/connection sensor":"Sensor kabel/verbinding",
    "Connected sensor states":"Statuswaarden aangesloten",
    "Disconnected sensor states":"Statuswaarden losgekoppeld",
    "Actual Charger power meter":"Vermogensmeter laadpaal",
    "Cumulative Charger energy meter":"Energiemeter laadpaal",
    "Native session sensor":"Sensor laadsessie",
    "Current setpoint Number":"Instelbare laadstroom",
    "Actual current sensor":"Sensor werkelijke laadstroom",
    "Rated Charger power":"Nominaal laadvermogen",
    "Connected phase count":"Aantal aangesloten fasen",
    "Connected phases":"Aangesloten fasen",
    "Nominal voltage":"Nominale spanning",
    "Hardware minimum current":"Minimumstroom hardware",
    "Hardware maximum current":"Maximumstroom hardware",
    "Supported current step":"Stroomregelstap",
    "Fixed current when connected":"Vaste laadstroom",
    "Supply circuit":"Voedingskring",
    "Circuit breaker limit":"Maximale stroomkring",
    "Configured minimum charging power":"Ingesteld minimum laadvermogen",
    "Configured maximum charging power":"Ingesteld maximum laadvermogen",
    "indicative variable energy":"indicatieve variabele energie"
  },
  fr:{
    "Complete object settings & sources":"Tous les paramètres et sources de cet objet",
    "Identity & strategy":"Identité et stratégie",
    "Energy & tariff sources":"Sources d'énergie et de tarifs",
    "Vehicle identity & lifetime":"Identité et validité du véhicule",
    "Goal & timing":"Objectif et horaires",
    "Price & charging decisions":"Prix et décisions de charge",
    "Battery & source references":"Batterie et sources",
    "Identity & ownership":"Identité et responsabilité",
    "Connection & meter sources":"Connexions et capteurs",
    "Electrical hardware & circuit":"Installation électrique et circuit",
    "Additional owner settings":"Autres paramètres",
    "Not configured":"Non configuré","Yes":"Oui","No":"Non",
    "Physical control owner":"Responsable de la commande",
    "Physically commissioned":"Mis en service physiquement",
    "Original vehicle at session time":"Véhicule de la session d'origine",
    "Complete object settings & sources":"Tous les paramètres et sources"
  },
  de:{
    "Complete object settings & sources":"Alle Einstellungen und Quellen dieses Objekts",
    "Identity & strategy":"Identität und Strategie",
    "Energy & tariff sources":"Energie- und Tarifquellen",
    "Vehicle identity & lifetime":"Fahrzeugidentität und Gültigkeit",
    "Goal & timing":"Ladeziel und Zeiten",
    "Price & charging decisions":"Preis- und Ladeentscheidungen",
    "Battery & source references":"Batterie und Datenquellen",
    "Identity & ownership":"Identität und Zuständigkeit",
    "Connection & meter sources":"Verbindung und Messgeräte",
    "Electrical hardware & circuit":"Elektrik und Stromkreis",
    "Not configured":"Nicht konfiguriert","Yes":"Ja","No":"Nein"
  },
  es:{
    "Complete object settings & sources":"Todos los ajustes y fuentes del objeto",
    "Identity & strategy":"Identidad y estrategia",
    "Energy & tariff sources":"Fuentes de energía y tarifas",
    "Vehicle identity & lifetime":"Identidad y vigencia del vehículo",
    "Goal & timing":"Objetivo y horarios",
    "Price & charging decisions":"Decisiones de precio y carga",
    "Battery & source references":"Batería y fuentes",
    "Identity & ownership":"Identidad y titularidad",
    "Connection & meter sources":"Conexión y contadores",
    "Electrical hardware & circuit":"Instalación eléctrica y circuito",
    "Not configured":"Sin configurar","Yes":"Sí","No":"No"
  },
  da:{
    "Complete object settings & sources":"Alle indstillinger og kilder for objektet",
    "Identity & strategy":"Identitet og strategi",
    "Energy & tariff sources":"Energi- og priskilder",
    "Vehicle identity & lifetime":"Køretøjets identitet og gyldighed",
    "Goal & timing":"Mål og tidspunkt",
    "Price & charging decisions":"Pris- og ladevalg",
    "Battery & source references":"Batteri og kilder",
    "Identity & ownership":"Identitet og ejerskab",
    "Connection & meter sources":"Forbindelse og målere",
    "Electrical hardware & circuit":"Elektrisk udstyr og kredsløb",
    "Not configured":"Ikke konfigureret","Yes":"Ja","No":"Nej"
  },
  nb:{
    "Complete object settings & sources":"Alle innstillinger og kilder for objektet",
    "Identity & strategy":"Identitet og strategi",
    "Energy & tariff sources":"Energi- og priskilder",
    "Vehicle identity & lifetime":"Kjøretøyets identitet og gyldighet",
    "Goal & timing":"Mål og tidspunkt",
    "Price & charging decisions":"Pris- og ladevalg",
    "Battery & source references":"Batteri og kilder",
    "Identity & ownership":"Identitet og eierskap",
    "Connection & meter sources":"Tilkobling og målere",
    "Electrical hardware & circuit":"Elektrisk utstyr og kurs",
    "Not configured":"Ikke konfigurert","Yes":"Ja","No":"Nei"
  },
  sv:{
    "Complete object settings & sources":"Alla inställningar och källor för objektet",
    "Identity & strategy":"Identitet och strategi",
    "Energy & tariff sources":"Energi- och priskällor",
    "Vehicle identity & lifetime":"Fordonets identitet och giltighet",
    "Goal & timing":"Mål och tidpunkt",
    "Price & charging decisions":"Pris- och laddval",
    "Battery & source references":"Batteri och källor",
    "Identity & ownership":"Identitet och ägarskap",
    "Connection & meter sources":"Anslutning och mätare",
    "Electrical hardware & circuit":"Elutrustning och krets",
    "Not configured":"Inte konfigurerad","Yes":"Ja","No":"Nej"
  }
};
for(const [locale,entries] of Object.entries(MC_OWNER_UX_LOCALES))
  Object.assign(MC_TEXT[locale],entries);
for(const [locale,label] of Object.entries({"da":"Interval for effektregulering","de":"Leistungsregelintervall","en":"Power adjustment interval","es":"Intervalo de ajuste de potencia","fr":"Intervalle de régulation de puissance","nb":"Intervall for effektregulering","nl":"Interval vermogensregeling","sv":"Intervall för effektreglering"})){
  if(MC_TEXT[locale])MC_TEXT[locale]["Power adjustment interval"]=label;
}

// A schema-aligned read-only projection of the ONE persisted Config Entry.
// Native entity controls and Options Flow below stay the only real writers.
const MC_OWNER_GROUPS = {
  controller: [
    ["Identity & strategy",[
      "id","name","mode","max_parallel","max_power_kw","power_adjustment_interval_minutes",
      "phase_limits_a","plan_label_mode","plan_color_by",
      "show_indicative_forecast"
    ]],
    ["Energy & tariff sources",[
      "price_entity","current_price_entity","export_price_entity",
      "solar_entity","solar_source_kind","solar_power_entity",
      "solar_surplus_entity","home_power_entity","grid_power_entity",
      "grid_power_direction","site_power_entity","binding_entity"
    ]]
  ],
  asset: [
    ["Vehicle identity & lifetime",[
      "id","name","kind","temporary","expires_at","plan_color"
    ]],
    ["Goal & timing",[
      "target_soc","requested_kwh","requested_duration_minutes",
      "requested_budget_amount","requested_budget_currency",
      "ready_by","ready_by_repeat","ready_by_weekdays",
      "charging_windows","earliest_start_at","expected_connection_at"
    ]],
    ["Price & charging decisions",[
      "continuous_charging","minimum_soc_pct","low_soc_trigger_pct",
      "maximum_price_per_kwh","price_currency","low_price_trigger_per_kwh",
      "opportunistic_kind","opportunistic_level_pct","priority"
    ]],
    ["Battery & source references",[
      "soc_entity","soc_stale_entity",
      "vehicle_control_entity","vehicle_current_entity",
      "capacity_kwh","max_charge_kw","charge_efficiency"
    ]]
  ],
  charger: [
    ["Identity & ownership",[
      "id","name","kind","asset","plan_color",
      "control_owner"
    ]],
    ["Connection & meter sources",[
      "control_entity","connected_entity","connected_states",
      "disconnected_states","power_entity","energy_entity",
      "session_entity","current_control_entity","current_readback_entity"
    ]],
    ["Electrical hardware & circuit",[
      "rated_power_kw","phase_count","phase_ids","voltage_v",
      "min_current_a","max_current_a","current_step_a","fixed_current_a",
      "circuit_id","circuit_limit_a","min_charging_power_kw",
      "max_charging_power_kw"
    ]]
  ]
};
const MC_OWNER_NAMES = {
  id:"Object ID",name:"Name",kind:"Type",asset:"Assigned vehicle",dedicated_asset_id:"Fixed vehicle assignment",
  mode:"Charging mode",max_parallel:"Simultaneous chargers",
  max_power_kw:"Site power ceiling",phase_limits_a:"Maximum per-phase current",
  power_adjustment_interval_minutes:"Power adjustment interval",
  plan_label_mode:"Plan labels",plan_color_by:"Colors represent",
  show_indicative_forecast:"Show unreserved forecast",
  price_entity:"Future tariff interval source",
  current_price_entity:"Current import price source",
  export_price_entity:"Current export price source",
  solar_entity:"Solar interval source",solar_source_kind:"Solar strategy",
  solar_power_entity:"Solar production sensor",
  solar_surplus_entity:"Available solar surplus sensor",
  home_power_entity:"Home consumption sensor",
  grid_power_entity:"Grid import/export sensor",
  grid_power_direction:"Grid sensor sign",
  site_power_entity:"Site capacity meter",
  binding_entity:"Power envelope source",
  temporary:"Temporary guest",expires_at:"Guest expires",
  plan_color:"Timeline color",target_soc:"Battery target",
  requested_kwh:"Extra energy goal",
  requested_duration_minutes:"Charging duration goal",
  requested_budget_amount:"Indicative budget goal",
  requested_budget_currency:"Budget currency",
  ready_by:"One-time Ready By",
  ready_by_repeat:"Ready By frequency",
  ready_by_weekdays:"Specific weekday Ready By times",
  charging_windows:"Allowed charging time windows",
  earliest_start_at:"Earliest charging start",
  expected_connection_at:"Expected connection time",
  continuous_charging:"Require continuous charging",
  minimum_soc_pct:"Minimum battery priority",
  low_soc_trigger_pct:"Early low-battery trigger",
  maximum_price_per_kwh:"Maximum price per kWh",
  price_currency:"Tariff currency",
  low_price_trigger_per_kwh:"Immediate low-price trigger",
  opportunistic_kind:"Opportunistic strategy",
  opportunistic_level_pct:"Opportunistic percentage",
  priority:"Vehicle charging priority",
  soc_entity:"Battery SoC sensor",
  soc_stale_entity:"Battery freshness sensor",
  vehicle_control_entity:"Vehicle-native command",
  vehicle_current_entity:"Vehicle-native current setting",
  capacity_kwh:"Usable battery capacity",
  max_charge_kw:"Vehicle charging limit",
  charge_efficiency:"Charging efficiency",
  control_owner:"Activation",
  physical_commissioned:"Physical commissioning",
  control_entity:"Native Charger control switch",
  connected_entity:"Cable/connection sensor",
  connected_states:"Connected sensor states",
  disconnected_states:"Disconnected sensor states",
  power_entity:"Actual Charger power meter",
  energy_entity:"Cumulative Charger energy meter",
  session_entity:"Native session sensor",
  current_control_entity:"Current setpoint Number",
  current_readback_entity:"Actual current sensor",
  rated_power_kw:"Rated Charger power",
  phase_count:"Connected phase count",
  phase_ids:"Connected phases",voltage_v:"Nominal voltage",
  min_current_a:"Hardware minimum current",
  max_current_a:"Hardware maximum current",
  current_step_a:"Supported current step",
  fixed_current_a:"Fixed current when connected",
  circuit_id:"Supply circuit",circuit_limit_a:"Circuit breaker limit",
  min_charging_power_kw:"Configured minimum charging power",
  max_charging_power_kw:"Configured maximum charging power"
};
const MC_OWNER_UNITS={
  max_power_kw:" kW",rated_power_kw:" kW",max_charge_kw:" kW",
  power_adjustment_interval_minutes:" min",
  min_charging_power_kw:" kW",max_charging_power_kw:" kW",
  capacity_kwh:" kWh",requested_kwh:" kWh",
  requested_duration_minutes:" min",maximum_price_per_kwh:" /kWh",
  low_price_trigger_per_kwh:" /kWh",min_current_a:" A",
  max_current_a:" A",fixed_current_a:" A",current_step_a:" A",
  circuit_limit_a:" A",voltage_v:" V",target_soc:"%",
  minimum_soc_pct:"%",low_soc_trigger_pct:"%",opportunistic_level_pct:"%"
};

const MC_EDIT_NUMBERS=new Set([
  "max_parallel","max_power_kw","power_adjustment_interval_minutes","target_soc","requested_kwh",
  "requested_duration_minutes","requested_budget_amount","minimum_soc_pct",
  "maximum_price_per_kwh","low_price_trigger_per_kwh","low_soc_trigger_pct",
  "opportunistic_level_pct","priority","capacity_kwh","max_charge_kw",
  "charge_efficiency","rated_power_kw","phase_count","voltage_v",
  "min_current_a","max_current_a","current_step_a","fixed_current_a",
  "circuit_limit_a","min_charging_power_kw","max_charging_power_kw"
]);
const MC_EDIT_BOOLEAN=new Set(["temporary","continuous_charging","show_indicative_forecast"]);
const MC_EDIT_DATES=new Set(["ready_by","expires_at","earliest_start_at","expected_connection_at"]);
const MC_EDIT_ENUM={
  control_owner:["external","multicharge"],
  mode:["Automatic","Solar","Economy","Ready By","Force Charge","Off"],
  plan_label_mode:["vehicle","charger","both"],
  plan_color_by:["vehicle","charger"],
  solar_source_kind:["none","intervals","grid_export","direct_surplus"],
  grid_power_direction:["import_positive","export_positive"],
  ready_by_repeat:["none","daily","weekly","specific_days"],
  opportunistic_kind:["off","type1","type2"],
  phase_count:["1","2","3"]
};
const MC_EDIT_SOURCE_DOMAINS={
  control_entity:["switch"],current_control_entity:["number"],
  current_readback_entity:["sensor"],connected_entity:["sensor","binary_sensor"],
  power_entity:["sensor"],energy_entity:["sensor"],session_entity:["sensor","binary_sensor"],
  soc_entity:["sensor"],soc_stale_entity:["binary_sensor"],
  vehicle_control_entity:["switch"],vehicle_current_entity:["number"]
};
for(const key of [
 "price_entity","current_price_entity","export_price_entity",
 "solar_entity","solar_power_entity","solar_surplus_entity",
 "home_power_entity","grid_power_entity","site_power_entity","binding_entity"
])MC_EDIT_SOURCE_DOMAINS[key]=["sensor"];
const MC_DAYS=["mon","tue","wed","thu","fri","sat","sun"];

function mcAssetGoalText(a){
  if(a.requested_budget_amount!==undefined)
    return a.requested_budget_amount+" "+(a.requested_budget_currency||"EUR")+
      " · "+mcTr("indicative variable energy");
  if(a.requested_duration_minutes!==undefined)
    return a.requested_duration_minutes+" "+mcTr("minutes");
  if(a.requested_kwh!==undefined)return a.requested_kwh+" kWh";
  if(a.target_soc!==undefined)return a.target_soc+"%";
  return mcTr("Not set");
}
function mcOwnerReadValue(value,field,timeZone){
  if(field==="control_owner")return mcTr(value==="multicharge"?"Active":"Inactive");
  if(value===undefined||value===null||value==="")return mcTr("Not configured");
  if(typeof value==="boolean")return mcTr(value?"Yes":"No");
  if(Array.isArray(value))return value.length?value.join(", "):mcTr("Not configured");
  if(typeof value==="object"){
    const pairs=Object.entries(value);
    if(!pairs.length)return mcTr("Not configured");
    return pairs.map(([key,v])=>{
      const detail=typeof v==="object"&&v!==null?
        (v.start&&v.end?v.start+"–"+v.end:
          Object.entries(v).map(([a,b])=>a+": "+b).join(", ")):
        String(v);
      return key.toUpperCase()+": "+detail;
    }).join(" · ");
  }
  if(/^(ready_by|earliest_start_at|expected_connection_at|expires_at)$/.test(field))
    return mcTime(value,timeZone);
  const unit=MC_OWNER_UNITS[field]||"";
  return String(value)+unit;
}

class RobotixMultiChargeCard extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    // User input belongs to the existing DOM until an explicit action.
    // A HA sensor/plan refresh is never permission to unmount a text field.
    this._unsavedInput=false;
    this.shadowRoot.addEventListener("input",event=>{
      const tag=String(event?.target?.tagName||"").toUpperCase();
      if(["INPUT","SELECT","TEXTAREA"].includes(tag))this._unsavedInput=true;
    },true);
    this._tab="Overview";
    this._day="today";
    this._filter="";
    this._preferenceKey=null;
    this._restoredFilter=null;
    this._noEntry=false;
    this._open="";
    this._folds={}; // disclosure-only UI state; never configuration or charging truth
    this._settingsOpen="";
    this._data=null;
    this._error="";
    this._last=0;
    this._loading=false;
    this._commandBusy=false;
    this._commandFeedback={};
    // Local, unsubmitted form values only; not an execution or settings store.
    this._manualDrafts={};
    this._calendarDrafts={};
    this._batteryDrafts={};
    this._batteryEditor="";
    this._windowsOpen="";
    this._settingsBusy=false;
    this._settingsFeedback=null;
    this._pendingSettings=null;
    this._assetEditor="";
    this._assignmentEditor="";
    this._goalDrafts={};
    this._goalEditor=""; // one visible novice goal form at a time
    this._scheduleEditor="";
    this._focusAsset="";
    this._fieldSequence=0;
    this._refreshTimer=null;
    this._refreshPending=false;
    this._historyFetchedAt=0;
    this._historyKey="";
    this._queryScope="";
    this._snapshotDay=null;
    this._pendingNative=null;
    this._editingField="";
    this._confirmDelete="";
    this._createCharger=false;
    this._yamlEditorOpen=false;
    this._yamlBaselineRevision=null;
    this._yamlCommittedRevision=null;
  }
  canManage(){return this._hass?.user?.is_admin===true&&!this._error;}
  canEditSettings(){return this.canManage()&&Boolean(this._data)&&!this._data.configuration_managed_by_yaml;}
  restoreViewPreferences(hass){
    // Browser-only display choices: never persist commands, goals or sources.
    const id=hass?.user?.id;
    if(!id)return;
    const key="robotix.multicharge.view.v1."+id;
    if(key===this._preferenceKey)return;
    this._preferenceKey=key;
    try{
      const saved=JSON.parse(globalThis.localStorage?.getItem(key)||"null");
      if(["today","tomorrow","both"].includes(saved?.day))this._day=saved.day;
      this._restoredFilter=typeof saved?.filter==="string"?saved.filter:"";
    }catch(_error){this._restoredFilter="";}
  }
  rememberViewPreferences(){
    if(!this._preferenceKey)return;
    try{globalThis.localStorage?.setItem(this._preferenceKey,
      JSON.stringify({day:this._day,filter:this._filter}));}catch(_error){}
  }
  validViewFilter(filter,configuration){
    return !filter||(configuration?.chargers||[]).some(x=>filter==="charger:"+x.id)||
      (configuration?.assets||[]).some(x=>filter==="asset:"+x.id);
  }
  selectViewRange(day,filter=this._filter){
    this._day=day;this._filter=filter;this._restoredFilter=null;
    this.rememberViewPreferences();
    this._last=0;
    if(this._loading)this._refreshPending=true;else void this.load();
  }
  watchedEntities(){
    const data=this._data||{},cfg=data.configuration||{},refs=data.preference_entities||{};
    const ids=new Set();
    for(const row of [cfg.controller,...(cfg.assets||[]),...(cfg.chargers||[])]){
      for(const [key,value] of Object.entries(row||{}))
        if(key.endsWith("_entity")&&typeof value==="string")ids.add(value);
    }
    for(const row of [refs.controller,...Object.values(refs.assets||{}),
                      ...Object.values(refs.chargers||{})])
      for(const value of Object.values(row||{}))
        if(typeof value==="string"&&value.includes("."))ids.add(value);
    return ids;
  }
  editingInProgress(){
    // Covers first-click keyboard focus (before an input event), entered
    // drafts even after blur, and editors still open without a focused field.
    const focused=this.shadowRoot?.activeElement;
    const tab=this._tab;
    const scopedEdit=Boolean(this._editingField&&(
      tab==="Settings"&&this._editingField.startsWith("controller:")||
      tab==="Chargeable Assets"&&this._editingField.startsWith("asset:")||
      tab==="Chargers"&&this._editingField.startsWith("charger:")));
    return Boolean(this._unsavedInput||scopedEdit||this._yamlEditorOpen||
      (this._batteryEditor&&["Overview","Chargeable Assets","Charging Plan"].includes(tab))||
      tab==="Overview"&&(this._assignmentEditor||this._goalEditor||this._scheduleEditor||this._assetEditor)||
      tab==="Chargeable Assets"&&(
        this._assetEditor||this._assignmentEditor||
        this._goalEditor||this._scheduleEditor||this._windowsOpen)||
      tab==="Chargers"&&this._createCharger||
      focused&&(focused.isContentEditable||
        ["INPUT","SELECT","TEXTAREA"].includes(
          String(focused.tagName||"").toUpperCase())));
  }
  passiveRender(){
    // Never rebuild shadowRoot on external HA state changes or late plan
    // responses while a human is editing. _data remains fresh in memory.
    if(this.editingInProgress())return;
    this.render();
  }
  showEditError(container=null){
    // A rejected validation/save updates feedback *in place*: never throw
    // away the value the resident just typed to explain why it was rejected.
    const target=container||this.shadowRoot?.querySelector?.(
      ".dashboard-field-edit, .dashboard-create, .quick-goal, .assignment-editor, .dashboard-editor, .root")||
      [...(this.shadowRoot?.children||[])].find(node=>node.className==="root");
    if(!target)return;
    const existing=typeof target.querySelector==="function"?
      target.querySelector("[data-mc-edit-error]"):null;
    const message=existing||mcEl("p","message error");
    const pending=this._settingsFeedback?.status==="accepted_unconfirmed";
    message.className="message "+(pending?"pending":"error");
    message.setAttribute("role",pending?"status":"alert");
    message.setAttribute("data-mc-edit-error","");
    message.textContent=mcTr(this._settingsFeedback?.message||"Unavailable");
    if(!existing)target.append(message);
  }
  scheduleSourceRefresh(){
    if(this._refreshTimer!==null)return;
    this._refreshTimer=setTimeout(()=>{
      this._refreshTimer=null;
      if(this._loading){this._refreshPending=true;return;}
      this._last=0;this.load();
    },this._error?5000:Math.max(350, 2500-(Date.now()-this._last)));
    // Does nothing in browsers; lets the source-only Node fixture exit.
    this._refreshTimer?.unref?.();
  }
  disconnectedCallback(){
    if(this._refreshTimer!==null)clearTimeout(this._refreshTimer);
    this._refreshTimer=null;
  }
  setConfig(config){this._cardConfig=config||{};this.passiveRender();}
  getCardSize(){return 10;}
  set hass(value){
    const before=this._hass;
    this._hass=value;
    this.restoreViewPreferences(value);
    if(this._pendingNative&&value?.states?.[this._pendingNative.entity]?.state===
        this._pendingNative.expected){
      this._pendingNative=null;
      this._settingsFeedback={status:"confirmed",message:"Saved"};
    }
    const changed=before&&this._data&&[...this.watchedEntities()].some(
      id=>before.states?.[id]!==value.states?.[id]
    );
    if(changed)this.scheduleSourceRefresh();
    else if(!this._loading&&(!this._last||Date.now()-this._last>60000))this.load();
    else if(this._data && before?.locale?.language!==value?.locale?.language)this.passiveRender();
  }
  async load(){
    if(!this._hass||this._loading)return;
    this._loading=true;if(!this._data)this.passiveRender();
    const requestedDay=this._day,requestedFilter=this._filter,requestedTab=this._tab;
    // A personal plan filter must not hide other vehicles' status/history.
    const queryFilter=requestedTab==="Charging Plan"?requestedFilter:"";
    try {
      const historyKey=requestedDay+"|"+queryFilter;
      const wantsHistory=["Overview","Charging Plan","Chargeable Assets","Chargers"].includes(this._tab);
      const beforeData=this._data;
      const cmd={type:"robotix_multicharge/get_plan",day:requestedDay,
        include_history:wantsHistory&&(!beforeData||this._historyKey!==historyKey||
          Date.now()-this._historyFetchedAt>=30000||
          beforeData.actual_history_quality==="NOT_REQUESTED")};
      if(queryFilter.startsWith("charger:"))cmd.charger_id=queryFilter.slice(8);
      if(queryFilter.startsWith("asset:"))cmd.asset_id=queryFilter.slice(6);
      const nextData=await this._hass.callWS(cmd);
      if(requestedDay!==this._day||
          queryFilter!==(this._tab==="Charging Plan"?this._filter:"")){
        this._refreshPending=true;return;
      }
      this._error="";this._noEntry=false;
      if(this._restoredFilter!==null){
        const restored=this._restoredFilter;
        this._restoredFilter=null;
        if(restored&&this.validViewFilter(restored,nextData.configuration)){
          this._filter=restored;this._refreshPending=true;
        }
        this.rememberViewPreferences();
      }else if(!this.validViewFilter(this._filter,nextData.configuration)){
        this._filter="";this.rememberViewPreferences();this._refreshPending=true;
      }
      if(cmd.include_history){
        this._historyKey=historyKey;this._historyFetchedAt=Date.now();
      }else if(beforeData&&this._historyKey===historyKey&&
        beforeData.start===nextData.start&&beforeData.end===nextData.end&&
        beforeData.configuration_revision===nextData.configuration_revision){
        nextData.actual_slots=beforeData.actual_slots;
        nextData.actual_history_quality=beforeData.actual_history_quality;
        nextData.observed_sessions=beforeData.observed_sessions;
        const key=r=>r.charger_id+"|"+r.started_at+"|"+r.ended_at;
        const prior=new Map([...(beforeData.completed_sessions||[]),...(beforeData.recent_completed_sessions||[])].map(r=>[key(r),r]));
        const fields=["estimated_variable_cost","estimated_variable_cost_currency","estimated_variable_cost_quality",
          "estimated_cost","estimated_cost_currency","estimated_cost_basis","observed_energy_kwh",
          "elapsed_minutes","average_power_kw","peak_power_kw"];
        for(const row of [...(nextData.completed_sessions||[]),...(nextData.recent_completed_sessions||[])]){
          const earlier=prior.get(key(row));
          if(earlier)for(const k of fields)if(earlier[k]!==undefined)row[k]=earlier[k];
        }
        for(const [uid,row] of Object.entries(nextData.active_sessions||{})){
          const earlier=beforeData.active_sessions?.[uid];
          if(earlier?.started_at===row.started_at)
            for(const k of fields)if(earlier[k]!==undefined)row[k]=earlier[k];
        }
      }else if(wantsHistory&&!cmd.include_history){
        this._historyFetchedAt=0;this._refreshPending=true;
      }
      if(this._data?.configuration_revision&&
         this._data.configuration_revision!==nextData.configuration_revision)
        this._manualDrafts={};
      const chargerIds=new Set((nextData.configuration?.chargers||[]).map(c=>c.id));
      for(const id of Object.keys(this._manualDrafts))
        if(!chargerIds.has(id))delete this._manualDrafts[id];
      this._data=nextData;
      this._queryScope=queryFilter;
      this._snapshotDay=requestedDay;
      if(this._yamlCommittedRevision&&
         this._data.configuration_revision===this._yamlCommittedRevision){
        this._yamlEditorOpen=false;
        this._yamlBaselineRevision=null;
        this._yamlCommittedRevision=null;
        this._unsavedInput=false;
        this._settingsFeedback={status:"confirmed",message:"Saved"};
      }
      if(this._pendingSettings&&
         this._data.configuration_revision===this._pendingSettings.expected_revision){
        const pending=this._pendingSettings;
        this._settingsFeedback={status:"confirmed",message:"Saved",scope:pending.scope,targetId:pending.targetId};
        this._pendingSettings=null;
        this._unsavedInput=false;
        if(pending.action==="create"&&pending.scope==="charger"){
          this._createCharger=false;this._open=pending.targetId;
        }
        if(pending.action==="create"&&pending.scope==="asset")this._assetEditor="";
        const prefix=pending.scope+":"+pending.targetId+":";
        if(this._editingField.startsWith(prefix)&&
            (pending.fields.includes(this._editingField.slice(prefix.length))||
             this._editingField===prefix+"setup"))this._editingField="";
        if(pending.scope==="asset"){
          const id=pending.targetId,fields=pending.fields||[];
          if(fields.includes("capacity_kwh")&&fields.includes("charge_efficiency")){
            delete this._batteryDrafts[id];if(this._batteryEditor===id)this._batteryEditor="";
          }
          if(fields.includes("ready_by_repeat")){
            delete this._calendarDrafts[id];if(this._scheduleEditor===id)this._scheduleEditor="";
          }
          if(fields.includes("requested_kwh")&&fields.includes("requested_duration_minutes")){
            delete this._goalDrafts[id];if(this._goalEditor===id)this._goalEditor="";
          }
        }
      }
      if(this._pendingSettings){
        if(Date.now()-this._pendingSettings.requestedAt>15000){
          this._pendingSettings=null;
          this._settingsFeedback={status:"rejected",message:"Save not confirmed; refresh and retry"};
          if(this.editingInProgress())this.showEditError();
        }else this._refreshPending=true;
      }
      this._last=Date.now();
    }catch(error){
      this._error=error && (error.message||error.code) ? String(error.message||error.code) : "Read access unavailable";
      this._noEntry=this._error.includes("NO_CONFIG_ENTRY");
      if(this._noEntry)this._data=null;
      // A deleted selection can make a filtered query invalid. Retry the
      // unfiltered snapshot, never show data from the wrong selected range.
      if(requestedFilter&&this._error.includes("Invalid plan scope")){
        this._filter="";this.rememberViewPreferences();this._refreshPending=true;
      }
      this._last=Date.now();
      if(!this._noEntry)this._refreshPending=true;
    }finally{
      this._loading=false;this.passiveRender();
      if(this._refreshPending){
        this._refreshPending=false;this.scheduleSourceRefresh();
      }
    }
  }
  async command(charger,action,manualRequest=null){
    if(this._commandBusy||!this._hass||!this.canManage())return;
    this._commandBusy=true;
    this._commandFeedback[charger]={status:"requested",reason:"Pending"};
    this.render();
    try {
      const request={type:"robotix_multicharge/command",
                     charger_id:charger,action};
      if(manualRequest)Object.assign(request,manualRequest);
      if(typeof crypto!=="undefined"&&typeof crypto.randomUUID==="function")
        request.request_id=crypto.randomUUID();
      const outcome=await this._hass.callWS(request);
      this._commandFeedback[charger]=outcome;
      if(outcome.status==="confirmed"){
        this._last=0;
        await this.load();
      }
    }catch(error){
      this._commandFeedback[charger]={
        status:"rejected",
        reason:"COMMAND_REQUEST_FAILED"
      };
    }finally{this._commandBusy=false;this.render();}
  }
  async saveSettings(scope,targetId,changes,action,structural=false){
    if(this._settingsBusy||this._pendingSettings||!this._hass||!this._data||!this.canEditSettings())return;
    const preserveDraft=this.editingInProgress();
    if(!this._data.configuration_revision){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      if(preserveDraft)this.showEditError();else this.render();
      return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Pending"};
    if(!preserveDraft)this.render();
    let admitted=false;
    try{
      const receipt=await this._hass.callWS({
        type:"robotix_multicharge/update_settings",
        scope,target_id:targetId,changes,action:action||"save",
        structural,
        expected_revision:this._data.configuration_revision
      });
      if(receipt.status!=="accepted_unconfirmed"||!receipt.expected_revision)
        throw new Error("Settings change was not admitted");
      this._pendingSettings={expected_revision:receipt.expected_revision,scope,targetId,action:action||"save",fields:Object.keys(changes),requestedAt:Date.now()};
      this._settingsFeedback={status:"accepted_unconfirmed",message:"Pending"};
      this._last=0;
      admitted=true;
      return true;
    }catch(error){
      const detail=[error?.message,error?.code].filter(Boolean).join(" ");
      const reason=detail.includes("CHARGER_BUSY_STOP_FIRST")?
        (Object.hasOwn(changes,"control_owner")?"Stop charging with the current owner before changing activation":"Stop charging before changing charger"):
        detail.includes("CHARGER_HAS_OTHER_ASSET")?
          "Unassign the other vehicle first":
        (detail.includes("STALE_SETTINGS_REFRESH")||detail.includes("stale_settings"))?
          "Settings changed; refresh and retry":
        detail.includes("STRUCTURAL_SAVE_REQUIRES_IDLE")?
          "Stop all managed chargers and verify idle power before changing electrical wiring or sources":
        detail.includes("SETTINGS_CONTROL_RECONCILIATION_REQUIRED")?
          "Reconcile outstanding charging commands before changing configuration":
        detail.includes("SETTINGS_PERSISTENCE_UNAVAILABLE")?
          "Settings could not be persisted; existing configuration retained":
        detail.includes("CHARGER_POWER_ENVELOPE_INVALID")?
          "Minimum and maximum power must fit the declared charger capacity":
        detail.includes("CHARGER_POWER_STEP_INVALID")?
          "No supported current step fits the configured power range":
        detail.includes("CHARGER_VOLTAGE_INVALID")?
          "Check the declared voltage per phase":
        detail.includes("CHARGER_PHASE_COUNT_INVALID")||detail.includes("CHARGER_PHASE_MAPPING_INVALID")?
          "Check phase count and phase mapping":
        detail.includes("DEDICATED_ASSIGNMENT_INVALID")?
          "Fixed assignment requires a permanent selected vehicle and connection source":
        detail.includes("SETTINGS_REJECTED")?
          "Settings rejected; check source, value and physical idle status":
          "Settings unavailable; check permissions, sources and connection";
      this._settingsFeedback={status:"rejected",message:reason};
      return false;
    }finally{
      this._settingsBusy=false;
      if(this._pendingSettings){if(this._loading)this._refreshPending=true;else await this.load();}
      if(preserveDraft&&(!admitted||this._pendingSettings))this.showEditError();
      else this.render();
    }
  }
  dashboardFieldControl(container,scope,record,field){
    // The UI is a typed projection of the established backend schema, never
    // a JSON document, separate settings store or native HA Options detour.
    const prior=record[field];
    if(field==="phase_limits_a"||field==="ready_by_weekdays"||
       field==="charging_windows"){
      const inputs={};
      const keys=field==="phase_limits_a"?["L1","L2","L3"]:MC_DAYS;
      for(const key of keys){
        const value=(prior||{})[key];
        if(field==="charging_windows"){
          const line=mcEl("div","dashboard-schedule-day");
          const enabled=this.field(line,key,value?"yes":"no",null,[
            ["no","Off"],["yes","On"]]);
          const start=this.field(line,"Start",value?.start||"22:00","time");
          const end=this.field(line,"End",value?.end||"06:00","time");
          inputs[key]={enabled,start,end};
          container.append(line);
        }else{
          const unit=field==="phase_limits_a"?" A":"";
          inputs[key]=this.field(container,key+unit,value??"",
            field==="phase_limits_a"?"number":"time");
        }
      }
      return ()=>{
        const result={};
        for(const key of keys){
          if(field==="charging_windows"){
            if(inputs[key].enabled.value==="yes"){
              const a=inputs[key].start.value,b=inputs[key].end.value;
              if(!a||!b||a===b)throw Error("Charging window requires different times");
              result[key]={start:a,end:b};
            }
          }else{
            const value=inputs[key].value;
            if(value!==""){
              const num=Number(value);
              if(field==="phase_limits_a"&&!Number.isFinite(num))
                throw Error("Invalid phase current");
              result[key]=field==="phase_limits_a"?num:value;
            }
          }
        }
        return Object.keys(result).length?result:null;
      };
    }
    if(field==="phase_ids"){
      const checked={};
      for(const key of ["L1","L2","L3"]){
        const input=mcEl("input");input.setAttribute("type","checkbox");
        input.checked=(prior||[]).includes(key);
        const label=mcEl("label","dashboard-check",key);
        label.append(input);container.append(label);checked[key]=input;
      }
      return ()=>{
        const values=Object.keys(checked).filter(key=>checked[key].checked);
        return values.length?values:null;
      };
    }
    if(field==="connected_states"||field==="disconnected_states"){
      const inp=this.field(container,"Native status names (comma separated)",
        Array.isArray(prior)?prior.join(", "):"","text");
      return ()=>{
        const values=inp.value.split(",").map(x=>x.trim()).filter(Boolean);
        return values.length?values:null;
      };
    }
    let options=null;
    if(field==="kind")options=scope==="charger"?
      ["on_off","variable_current"]:
      ["car","bicycle","motorcycle","scooter","other"];
    else if(field==="asset")options=["",...(this._data?.configuration?.assets||[]).map(x=>x.id)];
    else if(field==="dedicated_asset_id")options=["",...(record.asset?[record.asset]:[])];
    else if(field==="plan_color")options=Object.keys(this._data?.plan_palette||{});
    else options=MC_EDIT_ENUM[field]||null;
    if(MC_EDIT_BOOLEAN.has(field))options=["true","false"];
    if(options){
      const pairs=options.map(key=>[key,field==="control_owner"?(key==="multicharge"?mcTr("Active"):mcTr("Inactive")):key||mcTr("No vehicle")]);
      if(prior!==undefined&&!pairs.some(x=>x[0]===String(prior)))
        pairs.unshift([String(prior),String(prior)]);
      const choice=this.field(container,MC_OWNER_NAMES[field]||field,
        prior===undefined?"":String(prior),null,pairs);
      const read=()=>MC_EDIT_BOOLEAN.has(field)?
        choice.value==="true":MC_EDIT_NUMBERS.has(field)?
        (choice.value===""?null:Number(choice.value)):choice.value||null;
      read.setValue=value=>{choice.value=String(value??"");};return read;
    }
    const type=MC_EDIT_NUMBERS.has(field)?"number":"text";
    const fieldInput=this.field(container,MC_OWNER_NAMES[field]||field,
      prior===undefined||prior===null?"":prior,type);
    if(type==="number"){
      fieldInput.setAttribute("step",Number.isInteger(prior)&&prior!==null?"1":"any");
      fieldInput.setAttribute("inputmode","decimal");
    }
    if(MC_EDIT_SOURCE_DOMAINS[field]){
      const list=mcEl("datalist");
      const id="mc-source-"+scope+"-"+record.id+"-"+field;
      list.setAttribute("id",id);fieldInput.setAttribute("list",id);
      const domains=MC_EDIT_SOURCE_DOMAINS[field];
      const sources=Object.keys(this._hass?.states||{}).filter(name=>
        domains.includes(name.split(".")[0])).sort();
      for(const name of sources.slice(0,1500)){
        const option=mcEl("option");option.value=name;list.append(option);
      }
      container.append(list);
      container.append(mcEl("p","muted small",
        sources.length+" "+mcTr("registered Home Assistant sources")+" · "+
        mcTr("only existing native entities")));
    }
    if(MC_EDIT_DATES.has(field)){
      fieldInput.setAttribute("placeholder","YYYY-MM-DDTHH:mm:ss+01:00");
      container.append(mcEl("p","muted small",
        mcTr("Use an ISO timestamp with an explicit timezone")));
    }
    const read=()=>{
      const value=fieldInput.value.trim();
      if(!value)return null;
      if(MC_EDIT_NUMBERS.has(field)){
        const numeric=Number(value);
        if(!Number.isFinite(numeric))throw Error("Invalid number");
        return numeric;
      }
      return /currency$/.test(field)?value.toUpperCase():value;
    };
    read.setValue=value=>{fieldInput.value=String(value??"");};return read;
  }
  dashboardEditField(container,scope,record,field){
    const body=mcEl("div","dashboard-field-edit");
    let read=this.dashboardFieldControl(body,scope,record,field);
    const actions=mcEl("div","dashboard-edit-actions");
    const submit=mcButton(mcTr("Save"),async()=>{
      let value;
      try{value=read();}catch(e){
        this._settingsFeedback={status:"rejected",message:String(e.message)};
        this.showEditError(body);return;
      }
      const ok=await this.saveSettings(scope,record.id,{[field]:value},"save",true);
      if(ok&&this._settingsFeedback?.status==="confirmed"){this._editingField="";this.render();}
    });
    submit.disabled=this._settingsBusy||Boolean(this._pendingSettings);
    actions.append(submit,mcButton(mcTr("Cancel"),()=>{
      this._editingField="";this.render();
    }));
    body.append(actions);container.append(body);
  }
  dashboardDelete(container,scope,record){
    if(!this.canEditSettings()||scope==="controller")return;
    const key=scope+":"+record.id;
    const box=mcEl("div","dashboard-danger");
    if(this._confirmDelete===key){
      box.append(mcEl("span","muted small",
        mcTr("Confirm removal")+" · "+record.name+
        " · "+mcTr("Native history is retained")));
      box.append(mcButton(mcTr("Confirm removal"),async()=>{
        const ok=await this.saveSettings(scope,record.id,{},"delete",true);
        if(ok){this._confirmDelete="";this._open="";this.render();}
      }));
      box.append(mcButton(mcTr("Cancel"),()=>{
        this._confirmDelete="";this.render();
      }));
    }else box.append(mcButton(mcTr("Remove")+" "+record.name,()=>{
      this._confirmDelete=key;this.render();
    }));
    container.append(box);
  }
  ownerEntity(scope,uid,field){
    const prefs=this._data?.preference_entities||{};
    const group=scope==="controller"?prefs.controller:
      scope==="asset"?prefs.assets?.[uid]:prefs.chargers?.[uid];
    return group?.[field]||null;
  }
  async nativeSelect(scope,uid,field,option){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity||!this._hass?.callService){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Updating"};
    this.render();
    try{
      const expected=field==="mode"?MC_MODE_SELECT[option]||option:option;
      await this._hass.callService("select","select_option",{
        entity_id:entity,option:expected
      });
      this._pendingNative={entity,expected};
      this._last=0;
      await this.load();
      if(this._hass?.states?.[entity]?.state===expected){
        this._pendingNative=null;
        this._settingsFeedback={status:"confirmed",message:"Saved"};
      }else{
        this._settingsFeedback={status:"accepted_unconfirmed",message:"Updating"};
      }
    }catch(error){
      this._settingsFeedback={status:"rejected",message:String(error?.message||"Selection rejected").slice(0,210)};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeText(scope,uid,field,value){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity||!this._hass?.callService||this._settingsBusy)
      return;
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Updating"};
    try{
      await this._hass.callService("text","set_value",{entity_id:entity,value});
      this._pendingNative={entity,expected:value};
      this._last=0;await this.load();
      const observed=this._hass?.states?.[entity]?.state;
      const confirmed=observed===value;
      if(confirmed)this._pendingNative=null;
      this._settingsFeedback={
        status:confirmed?"confirmed":"accepted_unconfirmed",
        message:confirmed?"Saved":"Awaiting native state"
      };
    }catch(error){
      this._settingsFeedback={status:"rejected",
        message:String(error?.message||"Window settings rejected")};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeButton(scope,uid,field){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canManage()||!entity||!this._hass?.callService){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Pending"};
    this.render();
    try{
      await this._hass.callService("button","press",{entity_id:entity});
      this._last=0;
      await this.load();
      this._settingsFeedback={status:"confirmed",message:"Confirmed"};
    }catch(error){
      this._settingsFeedback={status:"rejected",message:"Unavailable"};
    }finally{this._settingsBusy=false;this.render();}
  }
  async nativeNumber(scope,uid,field,value){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||this._settingsBusy||!entity||
       typeof this._hass?.callService!=="function"||!Number.isFinite(value)){
      this._settingsFeedback={status:"rejected",message:"Unsupported number value"};
      this.render();return;
    }
    this._settingsBusy=true;
    this._settingsFeedback={status:"requested",message:"Applying"};
    this.render();
    try{
      await this._hass.callService("number","set_value",{
        entity_id:entity,value
      });
      this._last=0;
      await this.load();
      const state=this._hass?.states?.[entity]?.state;
      const confirmed=state!==undefined&&state!=="unknown"&&
        state!=="unavailable"&&Math.abs(Number(state)-value)<0.00001;
      // An EVSE may quantize a requested kW into real physical Amp steps:
      // never claim a requested setpoint equals physically measured power.
      this._settingsFeedback={
        status:confirmed?"confirmed":"accepted_unconfirmed",
        message:confirmed?"Saved":"Awaiting native HA/EVSE readback"
      };
      if(!confirmed&&field!=="set_charging_power_kw")
        this._pendingNative={entity,expected:String(value)};
    }catch(error){
      this._settingsFeedback={status:"rejected",message:String(
        error?.message||"Number rejected by Home Assistant"
      )};
    }finally{
      this._settingsBusy=false;this.render();
    }
  }
  nativeNumberEditor(container,scope,uid,field,label,fallback,unit=""){
    const entity=this.ownerEntity(scope,uid,field);
    if(!this.canEditSettings()||!entity)return;
    const native=this._hass?.states?.[entity];
    const state=native?.state;
    const observed=state!==undefined&&state!=="unavailable"&&
      state!=="unknown"&&state!==""&&Number.isFinite(Number(state))?
      Number(state):fallback;
    const row=mcEl("div","field native-number");
    const labelNode=mcEl("label","",mcTr(label)+(unit?" ("+unit+")":""));
    const control=mcEl("div","row");
    const input=mcEl("input");
    input.setAttribute("type","number");
    input.setAttribute("aria-label",mcTr(label));
    const controlId="multicharge-native-number-"+(this._fieldSequence++);
    input.setAttribute("id",controlId);
    labelNode.setAttribute("for",controlId);
    input.value=observed===undefined||observed===null?"":String(observed);
    const attr=native?.attributes||{};
    if(Number.isFinite(Number(attr.min))&&attr.min!==undefined)
      input.setAttribute("min",String(attr.min));
    if(Number.isFinite(Number(attr.max))&&attr.max!==undefined)
      input.setAttribute("max",String(attr.max));
    input.setAttribute("step",String(attr.step||0.01));
    const apply=mcButton(mcTr("Apply"),()=>{
      const value=Number(input.value);
      if(!input.value.trim()||!Number.isFinite(value)){
        this._settingsFeedback={status:"rejected",message:"Number required"};
        this.render();return;
      }
      void this.nativeNumber(scope,uid,field,value);
    });
    apply.disabled=this._settingsBusy||native?.state==="unavailable";
    control.append(input,apply);row.append(labelNode,control);
    container.append(row);
  }
  nativeRepeatEditor(container,asset){
    if(!this.canEditSettings())return;
    const zone=this._data?.timezone||"UTC";
    const parts=instant=>Object.fromEntries(new Intl.DateTimeFormat("en-CA",{
      timeZone:zone,year:"numeric",month:"2-digit",day:"2-digit",
      hour:"2-digit",minute:"2-digit",hourCycle:"h23"
    }).formatToParts(instant).map(p=>[p.type,p.value]));
    const today=parts(new Date());
    const anchor=asset.ready_by?parts(new Date(asset.ready_by)):null;
    const savedDays={...(asset.ready_by_weekdays||{})};
    if(asset.ready_by_repeat==="weekly"&&anchor&&!Object.keys(savedDays).length){
      const day=new Intl.DateTimeFormat("en-US",{timeZone:zone,weekday:"short"}).format(new Date(asset.ready_by)).toLowerCase();
      savedDays[day]=anchor.hour+":"+anchor.minute;
    }
    const savedTimes=Object.values(savedDays);
    const draft=this._calendarDrafts[asset.id]||{
      mode:asset.ready_by_repeat==="weekly"?"specific_days":asset.ready_by_repeat==="daily"?"daily":
        asset.ready_by_repeat==="specific_days"?"specific_days":asset.ready_by?"once":"none",
      date:anchor?anchor.year+"-"+anchor.month+"-"+anchor.day:today.year+"-"+today.month+"-"+today.day,
      clock:anchor?anchor.hour+":"+anchor.minute:savedTimes[0]||"",
      days:savedDays,overrides:new Set(savedTimes).size>1
    };
    const remember=()=>{this._calendarDrafts[asset.id]=draft;this._unsavedInput=true;};
    container.append(mcEl("h4","specific-day-calendar",mcTr("Charging days")));
    const choices=mcEl("div","chips schedule-modes");
    choices.setAttribute("aria-label",mcTr("Charging schedule"));
    for(const [mode,label] of [["once","Once"],["daily","Daily"],["specific_days","Specific days"],["none","No deadline"]]){
      const button=mcButton(mcTr(label),()=>{
        if(mode==="specific_days"&&draft.mode==="daily"&&!Object.keys(draft.days).length){
          for(const day of Object.keys(MC_DAY_NAMES))draft.days[day]=draft.clock;
        }
        draft.mode=mode;remember();this.render();
      },draft.mode===mode?"active":"");
      button.setAttribute("aria-pressed",String(draft.mode===mode));choices.append(button);
    }
    container.append(choices);
    if(draft.mode!=="none"){
      if(draft.mode==="specific_days"){
        const days=mcEl("div","chips schedule-days");
        for(const [day,label] of Object.entries(MC_DAY_NAMES)){
          const selected=Object.prototype.hasOwnProperty.call(draft.days,day);
          const button=mcButton(mcTr(label).slice(0,3),()=>{
            if(selected)delete draft.days[day];else draft.days[day]=draft.clock;
            remember();this.render();
          },selected?"active":"");
          button.setAttribute("aria-label",mcTr(label));button.setAttribute("aria-pressed",String(selected));days.append(button);
        }
        container.append(days);
      }
      const line=mcEl("div","goal-controls schedule-time");
      if(draft.mode==="once"){
        const date=this.field(line,mcTr("Date"),draft.date,"date");
        date.addEventListener("input",()=>{draft.date=date.value;remember();});
        date.addEventListener("change",()=>{draft.date=date.value;remember();});
      }
      const clock=this.field(line,mcTr("Ready By"),draft.clock,"time");
      const changeClock=()=>{
        const previous=draft.clock;draft.clock=clock.value;
        if(draft.mode==="specific_days"){
          for(const day of Object.keys(draft.days)){
            if(!draft.overrides||draft.days[day]===previous||!draft.days[day])draft.days[day]=clock.value;
          }
        }
        remember();
      };
      clock.addEventListener("input",changeClock);clock.addEventListener("change",()=>{changeClock();this.render();});
      container.append(line);
      if(draft.mode==="specific_days"){
        const toggle=mcButton(mcTr(draft.overrides?"Hide different times":"Different times per day"),()=>{
          draft.overrides=!draft.overrides;remember();this.render();
        });
        toggle.setAttribute("aria-expanded",String(draft.overrides));container.append(toggle);
        if(draft.overrides){
          const overrides=mcEl("div","goal-controls");
          for(const [day,label] of Object.entries(MC_DAY_NAMES)){
            if(!Object.prototype.hasOwnProperty.call(draft.days,day))continue;
            const time=this.field(overrides,mcTr(label),draft.days[day],"time");
            const update=()=>{draft.days[day]=time.value;remember();};
            time.addEventListener("input",update);time.addEventListener("change",update);
          }
          container.append(overrides);
        }
      }
    }
    const actions=mcEl("div","controls schedule-actions");
    const save=mcButton(mcTr("Save schedule"),async()=>{
      remember();
      let changes={ready_by_repeat:"none",ready_by:null,ready_by_weekdays:null};
      const validClock=value=>/^([01]\d|2[0-3]):[0-5]\d$/.test(value);
      const reject=message=>{this._settingsFeedback={status:"rejected",message};this.showEditError(container);};
      if(draft.mode==="specific_days"){
        if(!Object.keys(draft.days).length)return reject("Select at least one day");
        if(!Object.values(draft.days).every(validClock))return reject("Set Ready By time for selected days");
        changes.ready_by_repeat="specific_days";changes.ready_by_weekdays={...draft.days};
      }else if(draft.mode==="once"||draft.mode==="daily"){
        if(!validClock(draft.clock)||!draft.date)return reject("Set Ready By time");
        const localToday=today.year+"-"+today.month+"-"+today.day;
        if(draft.mode==="once"&&draft.date+"T"+draft.clock<=localToday+"T"+today.hour+":"+today.minute)
          return reject("Choose a future date and time");
        delete changes.ready_by;
        changes.ready_by_repeat=draft.mode==="daily"?"daily":"none";
        changes.ready_by_local=(draft.mode==="daily"?localToday:draft.date)+"T"+draft.clock+":00";
      }
      const accepted=await this.saveSettings("asset",asset.id,changes);
      if(accepted&&this._settingsFeedback?.status==="confirmed"){
        delete this._calendarDrafts[asset.id];this._scheduleEditor="";this.render();
      }
    });
    save.disabled=this._settingsBusy;
    save.className="active";
    actions.append(mcButton(mcTr("Cancel"),()=>{delete this._calendarDrafts[asset.id];this._scheduleEditor="";this.render();}),save);
    container.append(actions);
    this.nativeChargingWindowsEditor(container,asset);
  }
  nativeChargingWindowsEditor(container,asset){
    const available=Object.values(MC_DAY_NAMES).length;
    if(!available)return;
    const button=mcButton(mcTr("Allowed charging times"),()=>{
      this._windowsOpen=this._windowsOpen===asset.id?"":asset.id;
      this.render();
    });
    container.append(button);
    if(this._windowsOpen!==asset.id)return;
    const panel=mcEl("div","details");
    for(const [day,label] of Object.entries(MC_DAY_NAMES)){
      const field="charging_window_"+day;
      if(!this.ownerEntity("asset",asset.id,field))continue;
      const window=asset.charging_windows?.[day];
      const enabled=this.field(panel,mcTr(label),
        window?"on":"off",null,[
          ["off",mcTr("Window disabled")],["on",mcTr("Window enabled")]
        ]);
      const start=this.field(panel,mcTr(label)+" · "+mcTr("Start hour"),
        window?.start||"22:00","time");
      const end=this.field(panel,mcTr(label)+" · "+mcTr("End hour"),
        window?.end||"06:00","time");
      const save=()=>{
        if(enabled.value==="on"&&(!start.value||!end.value||
                                   start.value===end.value)){
          this._settingsFeedback={status:"rejected",
             message:"Start and end hours must differ"};
          this.render();return;
        }
        void this.nativeText("asset",asset.id,field,
          enabled.value==="on"?start.value+"-"+end.value:"");
      };
      for(const fieldNode of [enabled,start,end]){
        fieldNode.disabled=this._settingsBusy;
        fieldNode.addEventListener("change",save);
      }
    }
    container.append(panel);
  }
  openNative(scope,uid,field){
    if(!this.canEditSettings())return;
    this._editingField=scope+":"+uid+":"+field;
    if(scope==="controller"){this._tab="Settings";this._settingsOpen="Charging site";}
    else{this._tab=scope==="charger"?"Chargers":"Chargeable Assets";this._open=uid;}
    const group=(MC_OWNER_GROUPS[scope]||[]).find(([,fields])=>fields.includes(field));
    if(group)this._folds[scope+":"+uid+":"+group[0]]=true;
    this.render();
  }
  ownerColorControl(container,scope,row){
    const palette=this._data?.plan_palette||{};
    const entity=this.ownerEntity(scope,row.id,"plan_color");
    const options=Object.keys(palette).map(key=>[key,mcTr(key)]);
    const pick=this.field(container,"Plan color",row.plan_color,null,options);
    pick.disabled=!this.canEditSettings()||!entity||this._settingsBusy;
    pick.addEventListener("change",()=>this.nativeSelect(
      scope,row.id,"plan_color",pick.value
    ));
    return pick;
  }
  field(container,title,value,type,choices){
    const wrapper=mcEl("div","field"),label=mcEl("label","",title);
    const input=mcEl(choices?"select":"input");
    const id="multicharge-"+title.toLowerCase().replace(/[^a-z0-9]+/g,"-")+"-"+(this._fieldSequence++);
    input.setAttribute("id",id);label.setAttribute("for",id);
    if(choices){
      for(const [key,caption] of choices){
        const opt=mcEl("option","",caption);opt.value=key;
        if(key===String(value===null||value===undefined?"":value))opt.selected=true;
        input.append(opt);
      }
    }else{
      input.setAttribute("type",type||"text");
    }
    input.value=value===undefined||value===null?"":String(value);
    wrapper.append(label,input);container.append(wrapper);
    return input;
  }
  feedback(container){
    if(!this._settingsFeedback)return;
    const result=this._settingsFeedback;
    const label=result.status==="confirmed"?"Saved":result.status==="rejected"?(result.message||"Unavailable"):"Pending";
    const node=mcIconLabel(mcEl("p","message "+(result.status==="confirmed"?"confirmed":result.status==="rejected"?"error":"pending"),label),label,result.status==="confirmed"?"check-circle-outline":result.status==="rejected"?"alert-circle-outline":"clock-outline",result.status==="confirmed"?"good":result.status==="rejected"?"bad":"warn");
    node.setAttribute("role",result.status==="rejected"?"alert":"status");
    container.append(node);
  }
  title(container,label){
    container.append(mcEl("h2","",label));
  }
  notice(container,message,bad){
    container.append(mcIconLabel(mcEl("div","notice"+(bad?" error":""),message),message,bad?"alert-circle-outline":"information-outline",bad?"bad":"quiet"));
  }
  configure(container){
    // First installation only; configured runtime never navigates out for edits.
    if(this._hass?.user?.is_admin!==true||this._data||!this._noEntry)return;
    const link=mcEl("a","action",mcTr("Install MultiCharge once in Home Assistant"));
    link.href="/config/integrations/integration/robotix_multicharge";
    link.setAttribute("aria-label",mcTr("Home Assistant"));
    container.append(link);
  }
  render(){
    // Explicit Save/Cancel/navigation may repaint; passive refresh may not.
    this._unsavedInput=false;
    mcLanguage=String(this._hass?.locale?.language||this._hass?.language||"en").slice(0,2).toLowerCase();
    if(!this.shadowRoot)return;
    const root=this.shadowRoot;
    const oldCard=typeof root.querySelectorAll==="function"?
      [...root.querySelectorAll("[data-mc-object]")].find(el=>{
        const rect=el.getBoundingClientRect?.();
        return rect&&rect.bottom>0&&rect.top<(globalThis.innerHeight||900);
      }):null;
    const anchor=oldCard&&this._renderedTab===this._tab?
      {id:oldCard.getAttribute("data-mc-object"),top:oldCard.getBoundingClientRect().top}:null;
    this._renderedTab=this._tab;
    const previousCharts=typeof root.querySelectorAll==="function"?[...root.querySelectorAll(".mc-apex")]:[];
    root.replaceChildren();
    this._fieldSequence=0;
    const style=mcEl("style");style.textContent=MC_STYLE;root.append(style);
    const shell=mcEl("section","root");
    const head=mcEl("div","heading");const heading=mcEl("div");
    heading.append(mcEl("h2","","MultiCharge"));
    head.append(heading,mcButton("Refresh",()=>{this._historyFetchedAt=0;this._last=0;this.load();}));
    shell.append(head);
    const tabs=mcEl("nav","tabs");tabs.setAttribute("aria-label","MultiCharge views");
    for(const item of MC_TABS){
      const btn=mcButton(item,()=>{
        this._tab=item;
        // A main tab is a top-level destination, not the previous object drill-down.
        if(item==="Charging Plan"){
          this._filter="";this._restoredFilter=null;this.rememberViewPreferences();
        }
        this._yamlEditorOpen=false;
        this._yamlCommittedRevision=null;
        this.render();
        const scope=item==="Charging Plan"?this._filter:"";
        if(this._queryScope!==scope||
            (["Charging Plan","Chargeable Assets","Chargers"].includes(item)&&
             this._data?.actual_history_quality==="NOT_REQUESTED")){
          if(this._loading)this._refreshPending=true;else{this._last=0;this.load();}
        }
      });
      btn.setAttribute("aria-selected",String(this._tab===item));
      tabs.append(btn);
    }
    shell.append(tabs);
    if(this._loading&&!this._data)this.notice(shell,"Loading",false);
    if(this._error){
      this.notice(shell,this._noEntry?mcTr("Unavailable"):
        "Connection interrupted · "+this._error+(this._data?" · Last available data (read-only)":""),
        true);
      if(this._noEntry)this.configure(shell);
    }else if(!this._data&&!this._loading){
      this.notice(shell,"Unavailable",true);
    }
    if(this._data){
      if(this._tab==="Overview")this.overview(shell);
      if(this._tab==="Charging Plan")this.plan(shell);
      if(this._tab==="Chargeable Assets")this.assets(shell);
      if(this._tab==="Chargers")this.chargers(shell);
      if(this._tab==="Settings")this.settings(shell);

    }
    root.append(shell);
    if(typeof root.querySelectorAll==="function"){
      for(const plot of root.querySelectorAll(".mc-apex")){
        const existing=previousCharts.find(old=>old._mcApex&&old._mcSignature===plot._mcSignature&&typeof plot.replaceWith==="function");
        if(existing){
          previousCharts.splice(previousCharts.indexOf(existing),1);
          if(plot._mcLegend&&existing._mcLegend)plot._mcLegend.replaceWith(existing._mcLegend);
          plot.replaceWith(existing);
        }
      }
    }
    for(const old of previousCharts){try{old._mcApex?.destroy();}catch(_){}old._mcApex=null;}
    if(this._tab==="Charging Plan")mcSchedulePlanAlignment(root);
    if(anchor&&typeof root.querySelectorAll==="function"){
      const replacement=[...root.querySelectorAll("[data-mc-object]")].find(
        node=>node.getAttribute("data-mc-object")===anchor.id);
      if(replacement){
        const delta=replacement.getBoundingClientRect().top-anchor.top;
        if(Math.abs(delta)>1){
          let parent=this;
          while(parent){
            if(parent.scrollHeight>parent.clientHeight+1&&
                /auto|scroll/.test(globalThis.getComputedStyle?.(parent)?.overflowY||"")){
              parent.scrollTop+=delta;break;
            }
            parent=parent.parentElement||parent.getRootNode?.().host;
          }
          if(!parent)globalThis.scrollBy?.(0,delta);
        }
      }
    }
  }
  overview(container){
    const d=this._data,c=d.configuration||{},assets=c.assets||[],chargers=c.chargers||[];
    this.title(container,"Charging overview");
    const observations=(d.observations||{}).chargers||{};
    const sources=(d.observations||{}).sources||{};
    const priced=sources.current_price||{};
    const priceLabel=priced.quality==="ok"&&typeof priced.value==="number"&&priced.currency
      ?new Intl.NumberFormat(undefined,{style:"currency",currency:priced.currency,maximumFractionDigits:4}).format(priced.value)+"/kWh"
      :"Unavailable";
    const priceKind=priced.basis==="variable_reference"?
      "Variable reference price":priced.basis==="spot"?
        "Spot price":"Current price";
    const powers=chargers.map(x=>(observations[x.id]||{}).power_kw);
    const complete=powers.length>0&&powers.every(x=>x&&x.quality==="ok"&&typeof x.value==="number");
    const active=powers.filter(x=>x&&x.quality==="ok"&&x.value>0).length;
    const activated=chargers.filter(x=>x.control_owner==="multicharge"&&x.physical_commissioned===true).length;
    const metrics=mcEl("div","grid");
    for(const [key,value,source] of [
      ["Active chargers",String(activated)],
      ["Actual power",complete?(powers.reduce((sum,x)=>sum+x.value,0).toFixed(2)+" kW"):"Unknown"],
      [priceKind,priceLabel],
      ["Solar production",mcValue(sources.solar_power," kW"),sources.solar_power],
      ["Home consumption",mcValue(sources.home_power," kW"),sources.home_power],
      ["Grid power",mcValue(sources.grid_power," kW"),sources.grid_power]
    ]){const el=mcEl("div","metric");
      const tone=value==="Unknown"||value==="Unavailable"?"quiet":
        key==="Solar production"?"solar":key==="Actual power"&&active>0?"good":"";
      el.append(mcIconLabel(mcEl("p","muted small",key),key,mcIconFor(key),tone),mcEl("div","value",value));
      if(source&&source.quality!=="ok"){
        const last=source.last_reported_value;
        el.append(mcEl("p","muted small",typeof last==="number"?mcTr("Last reported")+" "+last+" kW · "+mcReason(source.reason):mcReason(source.reason)));
      }
      metrics.append(el);
    }
    const mode=(c.controller||{}).mode||"Off";
    const chips=mcEl("div","chips");chips.append(mcEl("p","muted",mcTr("Charging mode")+" · "+mode));
    for(const item of this.canEditSettings()?MC_MODES:[]){
      const button=mcButton(item,()=>this.nativeSelect("controller",(c.controller||{}).id,"mode",item));
      button.disabled=this._settingsBusy||item===mode||!this.ownerEntity("controller",(c.controller||{}).id,"mode");
      button.title=mcTr("Charging mode");
      if(item===mode)button.className="active";
      chips.append(button);
    }
    const site=mcEl("section","card charging-site-overview");
    site.append(mcEl("h3","",mcTr("Charging site")),metrics,chips);
    this.financialSummary(site,"controller","site");container.append(site);
    this.feedback(container);
    for(const charger of chargers){
      if(!(d.observed_sessions||[]).some(row=>row.charger_id===charger.id&&row.ongoing))continue;
      const activity=mcEl("div","card");activity.append(mcEl("h3","",charger.name));
      this.observedChargerActivity(activity,charger,true);container.append(activity);
    }
    const assetHeader=mcEl("div","row");
    assetHeader.append(mcEl("h3","",mcTr("Chargeable Assets")));
    if(this.canEditSettings()&&this._assetEditor!=="new")
      assetHeader.append(mcButton(mcTr("Add guest or vehicle"),()=>{
        this._assetEditor="new";this.render();
      }));
    container.append(assetHeader);this.assetCreate(container);
    const assetCards=mcEl("div","object-grid");container.append(assetCards);
    for(const a of assets){
      const card=mcEl("div","card");card.setAttribute("data-mc-object","asset:"+a.id);
      if(this._goalEditor===a.id||this._scheduleEditor===a.id||this._assignmentEditor===a.id||this._batteryEditor===a.id)card.className+=" expanded";
      const charger=chargers.find(x=>x.asset===a.id);
      const heading=mcEl("div","row");
      heading.append(mcIconLabel(mcEl("h3","",a.name),a.name,mcAssetIcon(a)),
        this.operationalIndicator(charger,a));
      card.append(heading);
      this.vehicleSummary(card,a,charger);
      this.goalAssessment(card,a,charger);
      this.financialSummary(card,"asset",a.id);
      const running=charger&&d.active_sessions?.[charger.id];
      if(running?.asset_id===a.id)this.sessionMetrics(card,running,false);
      if(a.temporary)card.append(mcEl("p","small",mcTr("Guest")+" · "+mcTime(a.expires_at,d.timezone)));
      const controls=mcEl("div","overview-actions");
      controls.append(mcButton(mcTr("Charging plan"),()=>{
        this._tab="Charging Plan";this.selectViewRange(this._day,"asset:"+a.id);
      }));
      if(this.canEditSettings()){
        controls.append(mcButton(mcTr("Set charging goal"),()=>{
          this._goalEditor=a.id;this._scheduleEditor="";this._assignmentEditor="";
          this.render();
        }));
        controls.append(mcButton(mcTr("Schedule charging"),()=>{
          this._scheduleEditor=this._scheduleEditor===a.id?"":a.id;
          this._goalEditor="";this._assignmentEditor="";this.render();
        }));
      }
      if(charger&&this.canManage()){
        const physical=(observations[charger.id]||{}).power_kw;
        const capabilities=(d.command_capabilities||{})[charger.id]||{};
        if(capabilities.stop_allowed&&physical?.quality==="ok"&&
            typeof physical.value==="number"&&physical.value>0){
          const stop=mcButton(mcTr("Stop charging"),()=>
            this.command(charger.id,"stop"));
          stop.disabled=this._commandBusy;
          controls.append(stop);
        }
      }
      // Keep the everyday action cluster together, including assignment and
      // explicit connected-vehicle confirmation; editors remain outside it.
      this.assetChargerAssignment(card,a,charger,chargers,controls);
      card.append(controls);
      if(this._goalEditor===a.id&&this.canEditSettings())this.assetGoalEditor(card,a);
      if(this._scheduleEditor===a.id&&this.canEditSettings()){
        const schedule=mcEl("div","details schedule-editor");
        schedule.append(mcEl("h4","",mcTr("When should the vehicle be ready?")));
        this.nativeRepeatEditor(schedule,a);card.append(schedule);
      }
      assetCards.append(card);
    }
    if(!assets.length&&chargers.length)this.notice(container,"No vehicles",false);
    const next=mcEl("div","card");next.append(mcEl("h3","","Next action"));
    next.append(mcEl("p","",!chargers.length?"Configure a charger to begin":d.status==="unavailable"?"Not ready":"Plan"));
    if(!chargers.length&&this.canEditSettings())
      next.append(mcButton(mcTr("Add charger"),()=>{
        this._tab="Chargers";this._createCharger=true;this.render();
      }));
    const reasons=Object.entries(d.reasons||{}).filter(([key,val])=>val!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",reasons.map(([key,val])=>key+": "+mcReason(val)).slice(0,4).join(" · ")));
    container.append(next);
  }
  plan(container){
    const d=this._data,c=d.configuration||{},controller=c.controller||{};
    const cars=c.assets||[],chargers=c.chargers||[];
    const labelMode=controller.plan_label_mode||"both";
    const colorBy=controller.plan_color_by||"vehicle";
    const forecastVisible=controller.show_indicative_forecast!==false;
    this.title(container,"Charging plan");
    if(!chargers.length){
      this.notice(container,"No charging points",false);
      this.configure(container);
      return;
    }
    const day=mcEl("div","controls");
    for(const chosen of ["today","tomorrow","both"]){
      const b=mcButton(chosen==="today"?"Today":chosen==="tomorrow"?"Tomorrow":"48h",()=>{
        this.selectViewRange(chosen);
      },this._day===chosen?"active":"");
      day.append(b);
    }
    const filter=mcEl("select");
    filter.setAttribute("aria-label","Filter by charger or vehicle");
    for(const [value,title] of [["","All chargers"],
      ...chargers.map(x=>["charger:"+x.id,x.name]),
      ...cars.map(x=>["asset:"+x.id,x.name+" (vehicle)"])]){
      const o=mcEl("option","",title);o.value=value;
      o.selected=this._filter===value;filter.append(o);
    }
    filter.value=this._filter;
    filter.addEventListener("change",()=>{this.selectViewRange(this._day,filter.value);});
    day.append(filter);
    if(this._filter)day.append(mcButton("All chargers",()=>this.selectViewRange(this._day,"")));
    container.append(day);
    const visibleCosts=[[d.view_planned_cost,"Planned charging cost"],
        [forecastVisible?d.view_indicative_cost:null,"Indicative charging cost"]]
      .filter(([row])=>row&&row.quality!=="no_planned_energy");
    if(visibleCosts.length){
      const costs=mcEl("section","card");
      for(const [row,label] of visibleCosts)this.planCostLine(costs,row,label);
      container.append(costs);
    }
    const selectors=mcEl("div","controls");
    const option=(title,setting,value,variants)=>{
      const wrap=mcEl("div","field");const label=mcEl("label","",title);
      const select=mcEl("select");
      select.setAttribute("aria-label",title);
      for(const [id,caption] of variants){
        const entry=mcEl("option","",caption);entry.value=id;
        if(id===value)entry.selected=true;
        select.append(entry);
      }
      select.value=value;
      select.disabled=!this.canEditSettings()||this._settingsBusy||!this.ownerEntity("controller",controller.id,setting);
      select.addEventListener("change",()=>{
        const selected=setting==="show_indicative_forecast"?
          select.value==="true":select.value;
        this.nativeSelect("controller",controller.id,setting,
          typeof selected==="boolean"?(selected?"on":"off"):selected);
      });
      wrap.append(label,select);selectors.append(wrap);
    };
    option("Show labels","plan_label_mode",labelMode,
      [["vehicle","Vehicle"],["charger","Charger"],["both","Vehicle + Charger"]]);
    option("Color by","plan_color_by",colorBy,
      [["vehicle","Vehicle"],["charger","Charger"]]);
    option("Indicative forecasting","show_indicative_forecast",
      String(forecastVisible),[["true","Show (not reserved)"],["false","Hide"]]);
    container.append(selectors);
    this.feedback(container);
    const rows=d.slots||[],forecast=forecastVisible?(d.forecast_slots||[]):[];
    const measured=d.actual_slots||[],assumptions=d.forecast_assumptions||{};
    const from=new Date(d.start).getTime(),until=new Date(d.end).getTime();
    const count=Math.max(1,Math.ceil((until-from)/900000));
    const width=820, x0=105, yRows=[28,54,80,106], height=14;
    const scene=mcEl("div");
    const shown=chargers.filter(item=>{
      if(!this._filter)return true;
      if(this._filter==="charger:"+item.id)return true;
      if(!this._filter.startsWith("asset:"))return false;
      const assetId=this._filter.slice(6);
      return item.asset===assetId ||
        [...rows,...forecast,...measured].some(s=>
          s.charger_id===item.id&&s.asset_id===assetId);
    });
    container.append(mcCombinedChargingChart(d,shown,rows,measured,forecastVisible?forecast:[]));
    if(!d.price_slots?.length){
      const msg=mcEl("div","card");msg.append(mcEl("p","muted small",mcTr("Future tariff intervals")+" · "+mcReason(d.observations?.sources?.tariff_quality||"SOURCE_NOT_SELECTED")));
      if(this.canEditSettings())msg.append(mcButton("Sources & bindings",()=>{this._tab="Settings";this._settingsOpen="Sources & bindings";this.render();}));
      container.append(msg);
    }
    const tomorrowQuality=d.observations?.sources?.tariff_tomorrow_quality;
    if(tomorrowQuality&&tomorrowQuality!=="OK"){
      const msg=mcEl("div","card");
      msg.append(mcEl("p","muted small",mcTr("Tomorrow")+" · "+mcTr("Future tariff intervals")+" · "+mcReason(tomorrowQuality)));
      container.append(msg);
    }
    container.append(mcEl("h3","",mcTr("Charging per vehicle and charger")));
    const values=[["proposed_power_kw",rows,"Proposed"],
      ["accepted_power_kw",rows,"Physically accepted"],
      ["actual_power_kw",measured,"Measured physical"],
      ["indicative_power_kw",forecast,"Indicative only"]];
    for(const charger of shown){
      const activeRows=rows.filter(s=>s.charger_id===charger.id);
      const previewRows=forecast.filter(s=>s.charger_id===charger.id);
      const actualRows=measured.filter(s=>s.charger_id===charger.id);
      const selected=cars.find(a=>a.id===charger.asset);
      const hasData=activeRows.length||previewRows.length||actualRows.length;
      const card=mcEl("section","plan-lane");
      const label=mcEl("div","row");
      const historicalAssetId=this._filter.startsWith("asset:")?
        this._filter.slice(6):null;
      const pastOnly=historicalAssetId&&charger.asset!==historicalAssetId;
      const historicAsset=cars.find(a=>a.id===historicalAssetId);
      const vehicleLabel=pastOnly?
        (historicAsset?historicAsset.name:historicalAssetId)+" (historical)":
        selected?selected.name:"No vehicle selected";
      const source=(d.observations||{}).chargers?.[charger.id]?.connected;
      const identity=(d.connection_identity||{})[charger.id];
      const verified=selected&&identity?.asset_id===selected.id;
      const plugged=source&&source.quality==="ok"?
        source.value?(verified?mcTr("Connected")+" · "+selected.name:
          mcTr("Connected")+" · "+mcTr("Vehicle unknown")):
        mcTr("Disconnected"):mcTr("Connection unknown");
      const fullName=labelMode==="vehicle"?vehicleLabel:
        labelMode==="charger"?charger.name:vehicleLabel+" · "+charger.name;
      const color=mcPlanOwnerColor(d,pastOnly?historicalAssetId:charger.asset,charger.id);
      const lhs=mcEl("div","plan-key");
      const swatch=mcEl("span","plan-swatch");swatch.style.background=color;
      lhs.append(swatch,mcEl("strong","",fullName));
      if(!pastOnly)lhs.append(this.operationalIndicator(charger,selected||null));
      label.append(lhs,mcEl("span","muted small",plugged));card.append(label);
      const readback=(d.observations||{}).assets?.[selected?.id]||{};
      const next=activeRows.find(item=>typeof item.proposed_power_kw==="number"&&
        Date.parse(item.end)>Date.now());
      const previewNext=previewRows.find(item=>typeof item.indicative_power_kw==="number"&&Date.parse(item.end)>Date.now());
      const reason=(d.reasons||{})[charger.id];
      const shortfall=(d.shortfall_kwh||{})[charger.id];
      const summary=mcEl("p","small lane-summary",
        mcTr("Battery")+" "+mcValue(readback.soc,"%")+" · "+
        mcTr("Target")+" "+(selected?.target_soc===undefined?mcTr("Not set"):
          selected.target_soc+"%")+" · "+mcTr("Ready By")+" "+
        mcTime(readback.next_ready_by??selected?.ready_by,d.timezone)+
        (next?" · "+mcTr("Next charge")+" "+
          mcTime(next.start,d.timezone)+" · "+next.proposed_power_kw+" kW":""));
      const hasGoal=!pastOnly&&selected&&d.goal_assessments?.[charger.id]?.asset_id===selected.id;
      if(!pastOnly&&selected){this.vehicleSummary(card,selected,charger);this.goalAssessment(card,selected,charger);}
      else card.append(summary);
      if(typeof shortfall==="number"&&shortfall>0&&!d.goal_assessments?.[charger.id])
        card.append(mcEl("p","plan-caution",mcTr("Shortfall")+" · "+
          shortfall.toFixed(2)+" kWh"));
      if(reason&&reason!=="PROPOSED"&&reason!=="TARGET_MET"&&
          (!hasGoal||d.goal_assessments[charger.id].reason!==reason))
        card.append(mcEl("p","plan-caution",mcReason(reason)));
      if(!assumptions[charger.id]&&forecastVisible&&d.forecast_reasons?.[charger.id]&&d.forecast_reasons[charger.id]!==reason)
        card.append(mcEl("p","plan-caution",mcTr("Indicative")+" · "+mcReason(d.forecast_reasons[charger.id])));
      if(actualRows.some(row=>row.asset_provenance!=="confirmed_closed_session"))
        card.append(mcEl("p","muted small",
          mcTr("Measured power is attributed to this charger; vehicle may be unknown")));
      if(!hasData){
        card.append(mcEl("p","muted small","No qualified slots for this day."));
      }else{
        card.append(mcApexLane(d,charger,activeRows,actualRows,previewRows));
      }
      if(assumptions[charger.id]&&forecastVisible&&(!hasGoal||!d.goal_assessments[charger.id].conditional)){
        if(previewNext)card.append(mcEl("p","small",mcTr("Indicative")+" · "+mcTime(previewNext.start,d.timezone)+" · "+previewNext.indicative_power_kw+" kW"));
        const forecastReason=d.forecast_reasons?.[charger.id];
        if(forecastReason&&forecastReason!=="PROPOSED")card.append(mcEl("p","plan-caution",mcReason(forecastReason)));
        const item=assumptions[charger.id];
        card.append(mcEl("p","plan-caution",mcTr("Indicative")+" · "+
          (item.assumption==="IF_ACTIVATED"?mcTr("If activated"):item.assumption==="IF_CONNECTED_NOW"?mcTr("If connected now"):
            item.assumption==="IF_SELECTED_VEHICLE_CONFIRMED"?mcTr("If selected vehicle is confirmed"):
            item.assumption==="IF_CAPABILITY_VERIFIED"?mcTr("If charger capability is verified"):
            mcTr("Expected")+" "+mcTime(item.assumed_connection_at,d.timezone))+
          " · "+mcTr("Not reserved")));
      }
      scene.append(card);
    }
    if(!shown.length)this.notice(scene,"No data",false);
    container.append(scene);
    const key=mcEl("div","legend");
    for(const phrase of ["Proposed","Accepted","Measured","Indicative"]){
      key.append(mcEl("span","",phrase));
    }
    container.append(key);
    const groups=Object.entries(assumptions).filter(([id,meta])=>
      forecastVisible&&(!this._filter||this._filter==="charger:"+id||
        this._filter==="asset:"+meta.asset_id));
    if(groups.length){
      const forecastInfo=mcEl("div","card");
      forecastInfo.append(mcEl("h3","",mcTr("Indicative")+" · "+mcTr(groups.every(([id,meta])=>meta.physically_connected===false||(d.observations?.chargers?.[id]?.connected?.quality==="ok"&&d.observations.chargers[id].connected.value===false))?"Disconnected":"Not reserved")));
      for(const [chargerId,meta] of groups){
        const obj=chargers.find(c=>c.id===chargerId);
        const car=cars.find(a=>a.id===meta.asset_id);
        const result=(d.forecast_reasons||{})[chargerId];
        const window=forecast.filter(s=>s.charger_id===chargerId);
        forecastInfo.append(mcEl("p","small",
          (car?car.name:meta.asset_id)+" · "+(obj?obj.name:chargerId)+
          " · "+(window.length?window.length+" × 15 min":mcTr("Unavailable"))+
          (result?" · "+mcReason(result):"")));
      }
      this.disclosure(container,"plan:forecast-summary","Indicative forecasting",forecastInfo,
        mcTr("Not reserved"));
    }
    if(!measured.some(row=>typeof row.actual_power_kw==="number")){
      this.notice(container,"Measured power unavailable",false);
    }
    const next=mcEl("div","card");
    next.append(mcEl("h3","","Next planned session"));
    const upcoming=rows.filter(s=>typeof s.proposed_power_kw==="number"&&s.proposed_power_kw>0)
      .sort((a,b)=>new Date(a.start)-new Date(b.start))[0];
    next.append(mcEl("p","",upcoming?
      mcPlanName(upcoming,c,labelMode)+" · "+mcTime(upcoming.start,d.timezone)+
      " · "+upcoming.proposed_power_kw+" kW":
      "No active plan"));
    const reasons=Object.entries(d.reasons||{}).filter(([,v])=>v!=="PROPOSED");
    if(reasons.length)next.append(mcEl("p","muted small",
      reasons.filter(([k])=>shown.some(charger=>charger.id===k))
        .map(([k,val])=>(chargers.find(charger=>charger.id===k)?.name||k)+" · "+mcReason(val)).join("; ")));
    container.append(next);
  }
  // One visible resident-readable goal control, one authorized atomic
  // settings transaction. Unsubmitted drafts are local form state only.
  chargerQuickSelection(container,charger){
    // Native Charger Device owns the *only* relationship. The card always
    // shows the chooser without opening Details; HA persists it once.
    const entity=this.ownerEntity("charger",charger.id,"asset");
    const select=mcEl("select","quick-vehicle-select");
    select.setAttribute("data-quick-assignment",charger.id);
    select.setAttribute("aria-label",mcTr("Selected vehicle")+" · "+charger.name);
    const assets=this._data?.configuration?.assets||[];
    const names=new Map();
    assets.forEach(a=>names.set(a.name,(names.get(a.name)||0)+1));
    const display=a=>names.get(a.name)>1?
      a.name+" ("+a.id+")":a.name;
    // HA Entity supplies the canonical choices. Source-derived names are
    // only a cold-start display fallback, never a second assignment writer.
    const state=entity?this._hass?.states?.[entity]:null;
    const nativeOptions=state?.attributes?.options;
    const options=Array.isArray(nativeOptions)&&nativeOptions.length?
      nativeOptions:["none",...assets.map(display)];
    const selected=assets.find(a=>a.id===charger.asset);
    const expected=selected?display(selected):"none";
    const current=options.includes(state?.state)?state.state:expected;
    for(const option of options){
      const item=mcEl("option","",option==="none"?
        mcTr("No vehicle"):option);
      item.value=option;select.append(item);
    }
    select.value=options.includes(current)?current:"none";
    select.disabled=!this.canEditSettings()||!entity||this._settingsBusy;
    select.addEventListener("change",()=>{
      const next=select.value;
      if(next!==current)void this.nativeSelect("charger",charger.id,"asset",next);
    });
    const wrap=mcEl("div","quick-assignment");
    const label=mcEl("label","",mcTr("Selected vehicle"));
    const id="mc-vehicle-"+charger.id.replace(/[^a-z0-9_-]/gi,"-");
    select.setAttribute("id",id);label.setAttribute("for",id);
    wrap.append(label,select);
    if(!entity)wrap.append(mcEl("span","muted small",
      mcTr("Native vehicle selection unavailable")));
    container.append(wrap);
  }
  disclosure(container,key,title,content,hint=""){
    // Native <details>/<summary> provides browser keyboard semantics and
    // independent compact disclosure, without an alternate page or state store.
    const fold=mcEl("details","owner-group object-disclosure");
    fold.open=this._folds[key]===true;
    fold.setAttribute("data-disclosure",key);
    fold.addEventListener("toggle",()=>{this._folds[key]=fold.open;});
    const summary=mcEl("summary","",mcTr(title));
    if(hint)summary.append(mcEl("span","owner-summary-count",hint));
    fold.append(summary,content);
    container.append(fold);
    return fold;
  }
  ownerFacts(container,scope,record,primaryFields=[]){
    // Every accepted persisted field appears under the one owning Device.
    // Details are compact by default and fold independently by stable ID.
    const groups=MC_OWNER_GROUPS[scope]||[];
    const wrapper=mcEl("section","owner-inventory");
    wrapper.append(mcEl("h4","",mcTr("Complete object settings & sources")));
    const covered=new Set();
    const renderField=(parent,field)=>{
      const label=MC_OWNER_NAMES[field]||field.replace(/_/g," ");
      const line=mcEl("div","owner-field");
      const info=mcEl("div","owner-field-info");
      info.append(mcEl("div","owner-field-label",mcTr(label)),
        mcEl("div","owner-field-value",
          mcOwnerReadValue(record[field],field,this._data?.timezone)));
      line.append(info);
      const key=scope+":"+record.id+":"+field;
      if(this.canEditSettings()&&!["id","physical_commissioned","dedicated_asset_id"].includes(field)&&
          !(scope==="charger"&&primaryFields.includes(field))){
        const edit=mcButton(mcTr("Edit"),()=>{
          if(primaryFields.includes(field)){
            this._settingsOpen=field==="phase_limits_a"?"Safety & limits":"Sources & bindings";
          }
          this._editingField=this._editingField===key?"":key;this.render();
        });
        edit.setAttribute("aria-label",mcTr("Edit")+" "+mcTr(label)+" · "+record.name);
        line.append(edit);
      }
      parent.append(line);
      if(this.canEditSettings()&&this._editingField===key&&!primaryFields.includes(field))
        this.dashboardEditField(parent,scope,record,field);
    };
    const fold=(title,fields,key)=>{
      const section=mcEl("details","owner-group");
      section.setAttribute("data-owner-group",key);
      section.open=this._folds[key]===true;
      section.addEventListener("toggle",()=>{this._folds[key]=section.open;});
      const summary=mcEl("summary","",mcTr(title));
      const configured=fields.filter(field=>
        record[field]!==undefined&&record[field]!==null&&record[field]!=="").length;
      summary.append(mcEl("span","owner-summary-count",
        configured+"/"+fields.length+" "+mcTr("configured fields")));
      section.append(summary);
      const fieldsNode=mcEl("div","owner-fields");
      fields.forEach(field=>renderField(fieldsNode,field));
      section.append(fieldsNode);
      wrapper.append(section);
    };
    for(const [title,fields] of groups){
      fields.forEach(field=>covered.add(field));
      fold(title,fields,scope+":"+record.id+":"+title);
    }
    // A newly supported source key may never disappear during a version
    // upgrade just because the bundled frontend is older than the backend.
    const extra=Object.keys(record).filter(key=>!covered.has(key)&&!(scope==="charger"&&key==="physical_commissioned"));
    if(extra.length)fold("Additional owner settings",extra,
      scope+":"+record.id+":additional");
    wrapper.append(mcEl("p","muted small",
      mcTr("Read from Home Assistant configuration")+" · "+
      Object.keys(record).length+" "+mcTr("configured fields")+" · "+
      mcTr("Missing values are not assumed")));
    if(this.canEditSettings())this.dashboardDelete(wrapper,scope,record);
    container.append(wrapper);
  }
  // Visual mapping only: reuse native physical state and evidence, never
  // confuse managed activation, configured current or planned power with draw.
  operationalIndicator(charger,asset=null){
    const d=this._data, state=d.charger_states?.[charger?.id]||{};
    const obs=d.observations?.chargers?.[charger?.id]||{};
    const power=asset?d.observations?.assets?.[asset.id]?.effective_power_kw:obs.power_kw;
    const connected=obs.connected?.quality==="ok"?obs.connected.value:null;
    const enabled=state.activation==="active"||
      (charger?.control_owner==="multicharge"&&charger?.physical_commissioned===true);
    const reasons=new Set([state.reason,state.goal_reason,d.reasons?.[charger?.id]]);
    const blocking=["CURRENT_PLUG_ASSET_UNCONFIRMED","CONTROL_STATE_UNVERIFIED",
      "PREVIOUS_COMMAND_UNCONFIRMED","CHARGER_CAPABILITY_UNQUALIFIED",
      "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED","CURRENT_RANGE_UNVERIFIED",
      "PHASE_WIRING_UNVERIFIED","PHYSICAL_PHASES_UNVERIFIED",
      "ELECTRICAL_WIRING_UNVERIFIED","NATIVE_CURRENT_CAPABILITY_MISMATCH",
      "NATIVE_CURRENT_CAPABILITY_UNVERIFIED","CURRENT_CONTROL_UNAVAILABLE",
      "NATIVE_SWITCH_UNAVAILABLE","INDEPENDENT_POWER_UNAVAILABLE",
      "POWER_SOURCE_UNAVAILABLE","OTHER_CHARGER_POWER_WITH_SWITCH_OFF",
      "POWER_ALREADY_PRESENT_WITHOUT_CONFIRMED_OWNER","SOC_SOURCE_UNAVAILABLE",
      "ASSET_SOC_UNAVAILABLE","BATTERY_CAPACITY_NOT_CONFIGURED",
      "CHARGE_EFFICIENCY_NOT_CONFIGURED","INVALID_PLANNING_INPUT"];
    const measured=power?.quality==="ok"&&Number.isFinite(power.value)&&power.value>0.05;
    const physicalDraw=obs.power_kw?.quality==="ok"&&obs.power_kw.value>0.05;
    const identity=d.connection_identity?.[charger?.id];
    const problem=Boolean(charger)&&(
      ["error","unavailable"].includes(state.charging_state)||
      obs.session?.value==="fault"&&obs.session?.quality==="ok"||
      (state.charging_session==="unknown"&&physicalDraw)||
      (enabled&&connected!==false&&(
        blocking.some(reason=>reasons.has(reason))||
        connected===null||
        (connected===true&&obs.power_kw?.quality!=="ok")||
        (connected===true&&charger.asset&&!identity?.asset_id)
      )));
    const goal=d.goal_assessments?.[charger?.id];
    const reached=asset&&goal?.asset_id===asset.id&&goal.status==="target_met";
    const actualFault=["error","unavailable"].includes(state.charging_state)||
      (obs.session?.value==="fault"&&obs.session?.quality==="ok")||
      (state.charging_session==="unknown"&&physicalDraw);
    const label=actualFault?"Problem":measured&&state.charging_session==="charging"?"Charging":
      reached&&!physicalDraw?"Goal reached":problem?"Problem":"Idle";
    const tone=label==="Problem"?"problem":label==="Charging"?"charging":label==="Goal reached"?"ready":"idle";
    const indicator=mcEl("span","operational-indicator "+tone,mcTr(label));
    indicator.setAttribute("data-operational-status",tone);
    const reason=blocking.find(code=>reasons.has(code))||state.reason||state.goal_reason;
    if(tone==="problem"){
      const explanation=reason?mcReason(reason):mcTr("Connection unknown");
      indicator.textContent=mcTr(label)+" · "+explanation;
      indicator.setAttribute("title",explanation);
    }else indicator.setAttribute("title",mcTr(label));
    return indicator;
  }
  vehicleSummary(card,asset,charger){
    const d=this._data,obs=d.observations?.assets?.[asset.id]||{};
    const connected=d.observations?.chargers?.[charger?.id]?.connected;
    const connection=charger?(connected?.quality==="ok"?
      (connected.value===true?mcTr("Connected"):mcTr("Disconnected")):mcTr("Connection unknown")):mcTr("Not assigned");
    const activation=charger?mcTr(charger.control_owner==="multicharge"&&charger.physical_commissioned===true?"Active":"Inactive"):"";
    const color=mcPlanOwnerColor(d,asset.id,charger?.id);
    const summary=mcEl("div","vehicle-summary");
    const row=mcEl("div","row");
    const goal=mcEl("div","vehicle-target");
    goal.append(mcEl("strong","vehicle-soc",mcValue(obs.soc,"%")),
      mcEl("span","muted small"," → "+mcAssetGoalText(asset)));
    const state=mcEl("div","vehicle-state muted small");
    state.append(mcEl("div","",connection+(activation?" · "+activation:"")),
      mcEl("div","",charger?.name||mcTr("No charger assigned")));
    row.append(goal,state);summary.append(row);mcSocBar(summary,obs.soc,color);
    const due=obs.next_ready_by!==undefined?obs.next_ready_by:asset.ready_by;
    const schedule=mcEl("div","row vehicle-deadline");
    const repeat=asset.ready_by_repeat==="daily"?mcTr("Daily"):
      ["weekly","specific_days"].includes(asset.ready_by_repeat)?mcTr("Specific days"):due?mcTr("Once"):mcTr("No deadline");
    schedule.append(mcEl("strong","",repeat),mcEl("span","",due?mcTr("Ready By")+" · "+mcTime(due,d.timezone):""));
    summary.append(schedule);card.append(summary);
  }
  goalTimeline(container,goal,color){
    const windows=goal.timeline_windows||[];
    const start=Date.parse(this._data.start),end=Date.parse(this._data.end);
    const deadline=Date.parse(goal.deadline);
    if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)return;
    const pos=value=>Math.max(0,Math.min(100,100*(value-start)/(end-start)));
    const block=mcEl("div","goal-timeline");
    block.setAttribute("aria-label",mcTr(goal.conditional?"Indicative charging plan":"Charging plan"));
    block.setAttribute("data-range-start",String(start));block.setAttribute("data-range-end",String(end));
    block.append(mcEl("div","muted small",mcTr(goal.conditional?"Indicative charging plan":"Charging plan")));
    const track=mcEl("div","goal-track");
    for(const item of windows){
      const a=Date.parse(item.start),b=Date.parse(item.end);
      if(!Number.isFinite(a)||!Number.isFinite(b)||b<=a||b<=start||a>=end)continue;
      const slot=mcEl("span","goal-window"+(goal.conditional?" conditional":""));
      slot.style.left=pos(a)+"%";slot.style.width=(pos(b)-pos(a))+"%";
      slot.style.background=color;slot.title=mcTime(item.start,this._data.timezone)+" – "+mcTime(item.end,this._data.timezone);
      track.append(slot);
    }
    if(Number.isFinite(deadline)&&deadline>=start&&deadline<=end){
      const marker=mcEl("span","goal-deadline-marker");
      marker.style.left=pos(deadline)+"%";marker.title=mcTr("Ready By")+" "+mcTime(goal.deadline,this._data.timezone);
      marker.setAttribute("aria-label",marker.title);track.append(marker);
    }
    block.append(track);
    const labels=mcEl("div","row goal-ticks muted small");
    for(const t of [start,start+(end-start)/4,start+(end-start)/2,start+(end-start)*3/4,end]){
      const tick=mcEl("span","",mcPlanTickText(t,this._data));
      tick.style.left=pos(t)+"%";
      tick.style.transform=t===start?"none":t===end?"translateX(-100%)":"translateX(-50%)";
      labels.append(tick);
    }
    block.append(labels);
    container.append(block);
  }
  goalAssessment(card,asset,charger){
    const goal=this._data?.goal_assessments?.[charger?.id];
    if(!goal||goal.asset_id!==asset.id)return;
    const labels={target_met:"Goal reached",achievable:"Goal achievable by deadline",
      planned:"Goal planned",shortfall:"Goal not covered by current plan",
      cannot_assess:"Cannot assess goal"};
    const good=goal.status==="target_met"||(goal.status==="achievable"&&!goal.conditional);
    const warn=["shortfall","cannot_assess"].includes(goal.status)||
      (goal.conditional&&goal.status!=="target_met");
    const result=mcEl("div","goal-outcome");
    result.setAttribute("data-goal-status",goal.status);
    const label=(goal.conditional&&goal.status!=="target_met"?mcTr("Indicative")+" · ":"")+
      mcTr(labels[goal.status]||"Cannot assess goal");
    result.append(mcIconLabel(mcEl("strong","goal-status "+(good?"confirmed":warn?"pending":""),label),
      label,good?"check-circle-outline":warn?"alert-circle-outline":"clock-outline",good?"good":warn?"warn":"quiet"));
    const metrics=mcEl("div","goal-metrics");
    for(const [field,caption] of [["required_grid_kwh","Required"],["planned_grid_kwh","Planned"],["shortfall_grid_kwh","Shortfall"]]){
      const cell=mcEl("div","goal-metric");
      cell.append(mcEl("span","muted small",mcTr(caption)),
        mcEl("strong","",typeof goal[field]==="number"&&Number.isFinite(goal[field])?goal[field].toFixed(2)+" kWh":mcTr("Unknown")));
      metrics.append(cell);
    }
    result.append(metrics);
    if((goal.timeline_windows||[]).length&&
        (!goal.conditional||this._data.configuration?.controller?.show_indicative_forecast!==false))
      this.goalTimeline(result,goal,mcPlanOwnerColor(this._data,asset.id,charger.id));
    const timing=[];
    if(goal.next_charge_at)timing.push(mcTr("Next charge")+" · "+mcTime(goal.next_charge_at,this._data.timezone));
    if(goal.planned_finish_at)timing.push(mcTr("Planned finish")+" · "+mcTime(goal.planned_finish_at,this._data.timezone));
    if(timing.length)result.append(mcEl("p","small goal-timing",timing.join("  |  ")));
    if(goal.conditional&&goal.status!=="target_met"){
      const assumption={IF_ACTIVATED:"If activated",IF_CONNECTED_NOW:"If connected now",
        IF_SELECTED_VEHICLE_CONFIRMED:"If selected vehicle is confirmed",IF_CAPABILITY_VERIFIED:"If charger capability is verified",USER_EXPECTED_CONNECTION_TIME:"Expected connection"};
      result.append(mcEl("p","muted small",mcTr("Indicative")+" · "+
        (assumption[goal.assumption]?mcTr(assumption[goal.assumption])+" · ":"")+mcTr("Not reserved")));
    }
    if(goal.reason&&goal.reason!=="PROPOSED"&&goal.reason!=="TARGET_MET")
      result.append(mcEl("p","muted small",mcReason(goal.reason)));
    if(typeof goal.session_draw_estimate?.power_kw==="number"&&goal.status!=="target_met"){
      result.append(mcEl("p","muted small",mcTr("Forecast from measured session power")+
        " · "+goal.session_draw_estimate.power_kw.toFixed(2)+" kW"));
    }
    if(goal.headroom_boost&&goal.status!=="target_met"){
      result.append(mcEl("p","muted small",mcTr("Conservative plan · available boost")+
        " "+Number(goal.maximum_reserved_power_kw).toFixed(2)+" kW"));
    }
    if(goal.deadline_recovery&&goal.status!=="target_met")
      result.append(mcEl("p","muted small",mcTr("Deadline recovery · higher verified setpoint, actual draw may differ")));
    if(goal.power_capability_verified===false&&goal.status!=="target_met"){
      const minimum=goal.minimum_planning_power_kw;
      result.append(mcEl("p","muted small",mcTr("Assumed minimum planning power")+
        (typeof minimum==="number"?" · "+minimum.toFixed(2)+" kW":"")));
    }
    card.append(result);
    const socGoal=asset.target_soc!==undefined&&
      ["requested_kwh","requested_duration_minutes","requested_budget_amount"].every(k=>asset[k]==null);
    if(socGoal&&goal.status!=="target_met"&&
      (asset.capacity_kwh==null||asset.charge_efficiency==null)){
      const missing=[asset.capacity_kwh==null?"Battery capacity":null,
        asset.charge_efficiency==null?"Charging efficiency":null].filter(Boolean);
      result.append(mcEl("p","plan-caution",missing.map(mcTr).join(" · ")));
      if(this.canEditSettings()){
        if(this._batteryEditor===asset.id)this.batteryEditor(result,asset);
        else result.append(mcButton(mcTr("Complete battery data"),()=>{
          this._batteryEditor=asset.id;this.render();
        }));
      }
    }
  }
  batteryEditor(container,asset){
    const draft=this._batteryDrafts[asset.id]||{
      capacity:asset.capacity_kwh??"",efficiency:asset.charge_efficiency==null?"":asset.charge_efficiency*100
    };
    const form=mcEl("div","goal-controls");
    const capacity=this.field(form,mcTr("Usable battery capacity (kWh)"),draft.capacity,"number");
    const efficiency=this.field(form,mcTr("Charging efficiency (%)"),draft.efficiency,"number");
    capacity.setAttribute("min","0.01");capacity.setAttribute("step","0.01");
    efficiency.setAttribute("min","0.01");efficiency.setAttribute("max","100");efficiency.setAttribute("step","0.1");
    const remember=()=>{this._batteryDrafts[asset.id]={capacity:capacity.value,efficiency:efficiency.value};this._unsavedInput=true;};
    capacity.addEventListener("input",remember);efficiency.addEventListener("input",remember);
    container.append(form,mcEl("p","muted small",mcTr("Use the vehicle's usable battery capacity and your charging efficiency estimate. No value is assumed.")));
    const actions=mcEl("div","controls");
    const save=mcButton(mcTr("Save battery data"),async()=>{
      remember();
      const kwh=Number(capacity.value),pct=Number(efficiency.value);
      if(!capacity.value.trim()||!efficiency.value.trim()||!Number.isFinite(kwh)||kwh<=0||!Number.isFinite(pct)||pct<=0||pct>100){
        this._settingsFeedback={status:"rejected",message:"Enter a positive capacity and efficiency between 0 and 100%"};this.showEditError(container);return;
      }
      const accepted=await this.saveSettings("asset",asset.id,{capacity_kwh:kwh,charge_efficiency:pct/100});
      if(accepted&&this._settingsFeedback?.status==="confirmed"){
        delete this._batteryDrafts[asset.id];this._batteryEditor="";this.render();
      }
    });
    save.disabled=this._settingsBusy;
    actions.append(save,mcButton(mcTr("Cancel"),()=>{delete this._batteryDrafts[asset.id];this._batteryEditor="";this.render();}));
    container.append(actions);
  }
  assetGoalEditor(card,asset){
    const kind=asset.requested_budget_amount!==undefined?"budget":
      asset.requested_duration_minutes!==undefined?"duration":
      asset.requested_kwh!==undefined?"energy":"soc";
    const original=kind==="budget"?asset.requested_budget_amount:
      kind==="duration"?asset.requested_duration_minutes:
      kind==="energy"?asset.requested_kwh:asset.target_soc;
    const stored=this._goalDrafts[asset.id];
    const draft=stored||{mode:kind,value:original===undefined?"":String(original)};
    if(!this.canEditSettings())return;
    const form=mcEl("section","quick-goal");
    form.append(mcEl("h4","",mcTr("Set charging goal")));
    const controls=mcEl("div","goal-controls");
    const goal=this.field(controls,mcTr("I want to charge to"),
      draft.mode,null,[
        ["soc",mcTr("Battery target (%)")],
        ["energy",mcTr("Extra energy (kWh)")],
        ["duration",mcTr("Charging time (minutes)")],
        ["budget",mcTr("Charging budget (€)")]
      ]);
    const amount=this.field(controls,mcTr("Amount"),draft.value,"number");
    amount.setAttribute("min",draft.mode==="soc"?"0":"0.01");
    amount.setAttribute("step",draft.mode==="duration"?"1":"0.01");
    goal.disabled=this._settingsBusy;
    amount.disabled=this._settingsBusy;
    goal.addEventListener("change",()=>{
      this._goalDrafts[asset.id]={mode:goal.value,value:""};
      this.render();
    });
    amount.addEventListener("input",()=>{
      this._goalDrafts[asset.id]={mode:goal.value,value:amount.value};
    });
    const action=mcButton(mcTr("Save charging goal"),()=>{
      const number=Number(amount.value);
      if(!amount.value.trim()||!Number.isFinite(number)||
          number<0||(goal.value!=="soc"&&number<=0)||
          (goal.value==="soc"&&number>100)||
          (goal.value==="duration"&&!Number.isInteger(number))||
          (goal.value==="budget"&&number>10000)){
        this._settingsFeedback={status:"rejected",message:"Invalid charging amount"};
        this.render();return;
      }
      const changes={
        requested_kwh:null,requested_duration_minutes:null,
        requested_budget_amount:null,requested_budget_currency:null
      };
      if(goal.value==="soc")changes.target_soc=number;
      if(goal.value==="energy")changes.requested_kwh=number;
      if(goal.value==="duration")changes.requested_duration_minutes=number;
      if(goal.value==="budget"){
        changes.requested_budget_amount=number;
        changes.requested_budget_currency="EUR";
      }
      void (async()=>{
        const accepted=await this.saveSettings("asset",asset.id,changes,"save");
        if(accepted&&this._settingsFeedback?.status==="confirmed"){
          delete this._goalDrafts[asset.id];this._goalEditor="";this.render();
        }
      })();
    });
    action.disabled=this._settingsBusy;
    form.append(controls,action,mcButton(mcTr("Cancel"),()=>{
      delete this._goalDrafts[asset.id];this._goalEditor="";this.render();
    }));
    if(draft.mode==="budget")form.append(mcEl("p","muted small",
      mcTr("Indicative energy budget, not a guaranteed electricity bill")));
    card.append(form);
  }
  assetChargerAssignment(card,a,charger,chargers,actions=card){
  if(this.canEditSettings()&&chargers.length){
    const change=mcButton(
      mcTr(charger?"Change charger":"Assign charger"),()=>{
        this._assignmentEditor=this._assignmentEditor===a.id?"":a.id;
        this._goalEditor="";this._scheduleEditor="";this.render();
      }
    );
    change.disabled=this._settingsBusy;
    actions.append(change);
    if(this._assignmentEditor===a.id){
      // A selected Vehicle belongs to exactly one Charger Config Entry
      // field. Do not silently replace a different assigned Vehicle.
      const candidates=chargers.filter(c=>!c.asset||c.asset===a.id);
      const editor=mcEl("div","details assignment-editor");
      editor.append(mcEl("p","muted small",
        "Idle-only reassignment. Stop charging separately before moving a vehicle."));
      if(candidates.length){
        const chooser=mcEl("select");
        chooser.setAttribute("aria-label",mcTr("Select charger"));
        for(const candidate of candidates){
          const option=mcEl("option","",candidate.name);
          option.value=candidate.id;
          chooser.append(option);
        }
        chooser.value=charger?.id||candidates[0].id;
        const apply=mcButton(mcTr("Assign selected charger"),()=>{
          if(!chooser.value||chooser.value===charger?.id)return;
          this.saveSettings("charger",chooser.value,{asset:a.id},"save");
        });
        apply.disabled=this._settingsBusy||
          !chooser.value||chooser.value===charger?.id;
        chooser.addEventListener("change",()=>{
          apply.disabled=this._settingsBusy||
            !chooser.value||chooser.value===charger?.id;
        });
        editor.append(chooser,apply);
      }else editor.append(mcEl("p","muted small","No free charger"));
      if(charger){
        const detach=mcButton(mcTr("Unassign charger"),()=>
          this.saveSettings("charger",charger.id,{asset:null},"save"));
        detach.disabled=this._settingsBusy;
        editor.append(detach);
      }
      editor.append(mcButton(mcTr("Close assignment"),()=>{
        this._assignmentEditor="";this.render();
      }));
      card.append(editor);
    }
  }
  }
  assets(container){
    const d=this._data,assets=d.configuration.assets||[],chargers=d.configuration.chargers||[];
    this.title(container,mcTr("Chargeable Assets")+" ("+assets.length+")");
    this.feedback(container);
    if(!assets.length)this.notice(container,"No vehicles",false);
    if(this.canEditSettings()&&this._assetEditor!=="new")container.append(mcButton("Add asset",()=>{
      this._assetEditor="new";this.render();
    }));
    this.assetCreate(container);
    const assetCards=mcEl("div","object-grid");container.append(assetCards);
    const arranged=this._focusAsset?
      [...assets].sort((a,b)=>(a.id===this._focusAsset?-1:0)-
                            (b.id===this._focusAsset?-1:0)):
      assets;
    if(this._focusAsset){
      const selected=assets.find(row=>row.id===this._focusAsset);
      if(selected)container.append(mcEl("p","small",
        mcTr("Selected vehicle")+" · "+selected.name));
    }
    for(const a of arranged){
      const card=mcEl("div","card object-card");card.setAttribute("data-mc-object","asset:"+a.id);const charger=chargers.find(x=>x.asset===a.id);
      const obs=((d.observations||{}).assets||{})[a.id]||{};
      const header=mcEl("div","row");header.append(mcIconLabel(mcEl("h3","",a.name),a.name,mcAssetIcon(a)),this.operationalIndicator(charger,a),mcButton(this._open===a.id?"Hide details":"Details",()=>{this._open=this._open===a.id?"":a.id;this.render();}));
      if(this._open===a.id||this._goalEditor===a.id||this._scheduleEditor===a.id||
          this._assignmentEditor===a.id||this._batteryEditor===a.id||this._editingField.startsWith("asset:"+a.id+":"))card.className+=" expanded";
      card.append(header);
      this.vehicleSummary(card,a,charger);
      this.goalAssessment(card,a,charger);
      this.financialSummary(card,"asset",a.id);
      card.append(mcEl("p","muted small",mcTr("Effective charging power")+" · "+mcValue(obs.effective_power_kw," kW")));
      // One explicit action opens the goal editor; the default view is a summary.
      const goalVisible=this._goalEditor===a.id;
      if(goalVisible)this.assetGoalEditor(card,a);
      else if(this.canEditSettings())card.append(mcButton(
        mcTr("Set charging goal"),()=>{
          this._goalEditor=a.id;this._scheduleEditor="";this._assignmentEditor="";this.render();
        }));
      if(this.canEditSettings()){
        const calendar=mcButton(
          this._scheduleEditor===a.id?mcTr("Hide charging schedule"):
            mcTr("Schedule charging"),()=>{
            this._scheduleEditor=this._scheduleEditor===a.id?"":a.id;
            this._goalEditor="";this._assignmentEditor="";this.render();
          });
        calendar.disabled=this._settingsBusy;
        card.append(calendar);
        if(this._scheduleEditor===a.id){
          const schedule=mcEl("div","details schedule-editor");
          schedule.append(mcEl("h4","",mcTr("When should the vehicle be ready?")));
          this.nativeRepeatEditor(schedule,a);
          card.append(schedule);
        }
      }
      this.assetChargerAssignment(card,a,charger,chargers);
      if(this._open===a.id){
        const detail=mcEl("div","details");
        mcPair(detail,"Charging priority",a.priority===undefined?"Not set":a.priority);
        mcPair(detail,"Battery data",obs.soc?(obs.soc.quality+" · "+(a.soc_entity||"manual")):"Unknown");
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"soc_entity")){
          const sourceEdit=mcEl("div","row");
          sourceEdit.append(mcEl("span","muted small",mcTr("Battery source")),
            mcButton(mcTr("Edit"),()=>this.openNative("asset",a.id,"soc_entity")));
          detail.append(sourceEdit);
        }
        mcPair(detail,"Requested energy",a.requested_kwh===undefined?"Not set":a.requested_kwh+" kWh");
        mcPair(detail,"Duration",a.requested_duration_minutes===undefined?"Not set":a.requested_duration_minutes+" min");
        mcPair(detail,mcTr("Charging budget"),
          a.requested_budget_amount===undefined?mcTr("Not set"):
          a.requested_budget_amount+" "+(a.requested_budget_currency||"EUR"));
        if(charger&&a.requested_budget_amount!==undefined){
          const current=(d.active_sessions||{})[charger.id];
          if(current?.budget_quality==="qualified_effective_meter_increments"||
             current?.budget_quality==="conservative_effective_upper_bound"){
            const conservative=current.budget_quality==="conservative_effective_upper_bound";
            mcPair(detail,mcTr(conservative?"Conservative budget upper bound":
              "Indicative variable spending"),
              Number(current.budget_cost||0).toFixed(2)+" "+
              (current.requested_budget_currency||"EUR"));
            mcPair(detail,mcTr(conservative?"Budget remaining (conservative)":
              "Budget remaining"),
              Math.max(0,a.requested_budget_amount-(current.budget_cost||0)).toFixed(2)+
              " "+(current.requested_budget_currency||"EUR"));
          }else if(current?.requested_budget_amount!=null)
            mcPair(detail,mcTr("Budget progress"),mcTr("Unavailable"));
        }
        const preferences=mcEl("div","owner-fields preference-grid");
        for(const [field,label,unit] of [
          ["target_soc","Charging limit","%"],
          ["requested_kwh","Requested energy","kWh"],
          ["requested_duration_minutes","Requested charging duration","minutes"],
          ["requested_budget_amount","Requested budget (€)","EUR"],
          ["minimum_soc_pct","Minimum charge before price limits","%"],
          ["maximum_price_per_kwh","Price ceiling per kWh","currency/kWh"],
          ["low_price_trigger_per_kwh","Immediate low-price threshold","currency/kWh"],
          ["low_soc_trigger_pct","Immediate low-SoC threshold","%"],
          ["opportunistic_level_pct","Opportunistic percentage","%"],
          ["max_charge_kw","Maximum vehicle charging power","kW"],
          ["priority","Priority",""],
          ["capacity_kwh","Battery capacity","kWh"],
          ["charge_efficiency","Charging efficiency",""]
        ])this.nativeNumberEditor(preferences,"asset",a.id,field,label,a[field],unit);
        this.disclosure(detail,"asset:"+a.id+":preferences",
          "Charging preferences",preferences);
        const deadline=mcEl("div","row");
        deadline.append(mcEl("span","",mcTr("Ready By")+" · "+mcTime(a.ready_by,d.timezone)));
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"ready_by"))
          deadline.append(mcButton(mcTr("Set charging deadline"),()=>
            this.openNative("asset",a.id,"ready_by")));
        detail.append(deadline);
        // Schedule has one resident editor; native owner fields remain in Details.
        // Native upstream price/SoC policy remains Asset-owned and one
        // Config Entry preference; this view never stores price decisions.
        mcPair(detail,mcTr("Price currency"),
          a.price_currency||mcTr("Choose currency before price limits"));
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"price_currency")){
          const edit=mcButton(mcTr("Set price currency"),()=>
            this.openNative("asset",a.id,"price_currency"));
          edit.disabled=this._settingsBusy;
          detail.append(edit);
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"earliest_start_at")){
          detail.append(mcButton(mcTr("Set earliest start"),()=>
            this.openNative("asset",a.id,"earliest_start_at")));
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"opportunistic_kind")){
          const strategy=this.field(detail,mcTr("Opportunistic charging"),
            a.opportunistic_kind||"off",null,[
              ["off",mcTr("Off")],["type1",mcTr("Type 1 — cap fraction")],
              ["type2",mcTr("Type 2 — tomorrow price")],
            ]);
          strategy.disabled=this._settingsBusy;
          strategy.addEventListener("change",()=>
            void this.nativeSelect("asset",a.id,"opportunistic_kind",
                                   strategy.value));
        }
        if(this.canEditSettings()&&this.ownerEntity("asset",a.id,"continuous_charging")){
          detail.append(mcEl("h4","",mcTr("Continuity and price strategy")));
          const continuity=this.field(
            detail,mcTr("Charging pattern"),
            a.continuous_charging?"continuous":"flexible",null,[
              ["flexible",mcTr("Flexible cheapest quarters")],
              ["continuous",mcTr("One continuous charge")],
            ]);
          continuity.disabled=this._settingsBusy;
          continuity.addEventListener("change",()=>
            void this.nativeSelect("asset",a.id,
                                  "continuous_charging",continuity.value));
        }
        if(this.canEditSettings())this.ownerColorControl(detail,"asset",a);
        for(const [field,label] of [
          ["kind","Asset type"],["expected_connection_at","Expected"],
          ["expires_at","Guest expiry"],["name","Asset name"]
        ]){
          if(!this.canEditSettings()||!this.ownerEntity("asset",a.id,field))continue;
          const row=mcEl("div","row");
          row.append(mcEl("span","muted small",label),mcButton("Edit",
            ()=>this.openNative("asset",a.id,field)));
          detail.append(row);
        }
        this.ownerFacts(detail,"asset",a);
        const recent=(d.recent_completed_sessions||d.completed_sessions||[])
          .filter(entry=>entry.asset_id===a.id&&entry.physical_stop_confirmed===true)
          .slice(-3).reverse();
        const historyPanel=mcEl("div","history-values");
        if(!recent.length)historyPanel.append(mcEl("p","muted small",
          mcTr("No confirmed charging history")));
        for(const receipt of recent){
          const row=mcEl("div","owner-group");
          mcPair(row,mcTr("Charger at session time"),
            chargers.find(ch=>ch.id===receipt.charger_id)?.name||
              receipt.charger_id||mcTr("Unknown"));
          mcPair(row,mcTr("Completed"),mcTime(receipt.ended_at,d.timezone));
          this.sessionMetrics(row,receipt,false);
          mcPair(row,mcTr("Physical STOP confirmed"),mcTr("Yes"));
          if(receipt.stop_reason)mcPair(row,mcTr("Session stop reason"),
            mcReason(receipt.stop_reason));
          historyPanel.append(row);
        }
        this.disclosure(detail,"asset:"+a.id+":history",
          "Vehicle charging history",historyPanel,
          recent.length+" "+mcTr("configured fields"));
        card.append(detail);
      }
      assetCards.append(card);
    }
  }
  assetCreate(container){
    const d=this._data;
    if(this.canEditSettings()&&this._assetEditor==="new"){
      const form=mcEl("form","card dashboard-create");form.append(mcEl("h3","","Add a chargeable asset"));
      const name=this.field(form,"Asset name","","text");
      const kind=this.field(form,"Asset type","car",null,[
        ["car",mcTr("Car")],["bicycle",mcTr("Bicycle")],
        ["motorcycle",mcTr("Motorcycle")],["scooter",mcTr("Scooter")],
        ["other",mcTr("Other")]
      ]);
      const goal=this.field(form,mcTr("Charging goal"),"soc",null,[
        ["soc",mcTr("Battery target (%)")],["energy",mcTr("Energy (kWh)")],
        ["duration",mcTr("Duration (minutes)")],["budget",mcTr("Budget (€)")],
        ["none",mcTr("Set later")]
      ]);
      const amount=this.field(form,mcTr("Charging amount"),"80","number");
      form.append(mcEl("p","muted small","New permanent cars: Daily · 06:00 (local time)."));
      kind.addEventListener("change",()=>{goal.value=kind.value==="car"?"soc":"none";amount.value=kind.value==="car"?"80":"";});
      goal.addEventListener("change",()=>{amount.value=goal.value==="soc"?"80":"";});
      const free=(d.configuration.chargers||[]).filter(ch=>!ch.asset);
      const assigned=this.field(form,mcTr("Select free charger (optional)"),
        "none",null,[["none",mcTr("Assign later")],
                    ...free.map(ch=>[ch.id,ch.name])]);
      const temporary=this.field(form,"Temporary guest","no",null,
        [["yes","Yes — temporary guest"],["no","No — permanent asset"]]);
      const expiry=this.field(form,mcTr("Guest for"),"24",null,[
        ["4",mcTr("4 hours")],["24",mcTr("24 hours")],
        ["48",mcTr("48 hours")],["168",mcTr("7 days")]
      ]);
      form.append(mcButton("Create asset",()=>{
        const id=name.value.trim().toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
        const changes={name:name.value.trim(),kind:kind.value};
        if(assigned.value!=="none")
          changes.assign_charger_id=assigned.value;
        const requested=amount.value.trim();
        if(goal.value!=="none"&&requested){
          const value=Number(requested);
          if(!Number.isFinite(value)||value<0||
              (goal.value!=="soc"&&value===0)||(goal.value==="soc"&&value>100)||
              goal.value==="duration"&&!Number.isInteger(value)){
            this._settingsFeedback={status:"rejected",message:"Invalid charging amount"};
            this.showEditError(form);return;
          }
          if(goal.value==="soc")changes.target_soc=value;
          if(goal.value==="energy")changes.requested_kwh=value;
          if(goal.value==="duration")changes.requested_duration_minutes=value;
          if(goal.value==="budget"){
            changes.requested_budget_amount=value;
            changes.requested_budget_currency="EUR";
          }
        }
        if(temporary.value==="yes"){
          changes.temporary=true;
          // Relative expiry is a real absolute UTC instant; browser local
          // timezone cannot silently reinterpret a household wall clock.
          changes.expires_at=new Date(Date.now()+Number(expiry.value)*3600000).toISOString();
        }
        this.saveSettings("asset",id,changes,"create");
      }));
      form.append(mcButton(mcTr("Cancel"),()=>{this._assetEditor="";this.render();}));
      container.append(form);
    }
  }
  dashboardChargerCreate(container){
    if(!this.canEditSettings())return;
    const box=mcEl("section","card dashboard-create");
    box.append(mcEl("h3","",mcTr("Add charger")+" · "+
      mcTr("configured entirely in MultiCharge")));
    box.append(mcEl("p","muted small",
      "Active allows MultiCharge control. Inactive retains monitoring. Save sends no charging command."));
    const id=this.field(box,mcTr("Stable charger ID"),"","text");
    const name=this.field(box,mcTr("Charger name"),"","text");
    const kind=this.field(box,mcTr("Control type"),"on_off",null,[
      ["on_off",mcTr("On/off")],["variable_current",mcTr("Variable current")]
    ]);
    const owner=this.field(box,mcTr("Activation"),"multicharge",null,[
      ["external",mcTr("Inactive")],["multicharge",mcTr("Active")]
    ]);
    const readSwitch=this.dashboardFieldControl(box,"charger",{id:"new_charger"},"control_entity");
    const power=this.field(box,mcTr("Rated power (kW)"),"","number");
    power.setAttribute("step","any");
    const tech=mcEl("details","owner-group");
    tech.append(mcEl("summary","",mcTr("Native connection, power and current sources")));
    const panel=mcEl("div","owner-fields");
    const draft={id:"new_charger"};
    const readers={};
    for(const field of [
      "connected_entity","connected_states","disconnected_states",
      "power_entity","energy_entity","session_entity",
      "current_control_entity","current_readback_entity",
      "phase_count","phase_ids","voltage_v",
      "min_current_a","max_current_a","current_step_a","fixed_current_a",
      "circuit_id","circuit_limit_a"
    ])readers[field]=this.dashboardFieldControl(panel,"charger",draft,field);
    tech.append(panel);
    const discovery=mcEl("div","small muted");
    const discover=mcButton("Discover native sources",async()=>{
      const control=readSwitch();
      if(!control){discovery.textContent="Select the native charger switch first.";return;}
      const selectedKind=kind.value;
      discover.disabled=true;
      try{
        const response=await this._hass.callWS({type:"robotix_multicharge/get_plan",
          day:this._day,include_history:false,discover_charger:{control_entity:control,kind:selectedKind}});
        if(readSwitch()!==control||kind.value!==selectedKind)return;
        const setup=response.charger_setup_draft;
        if(!setup)throw Error("Native discovery unavailable");
        let count=0;
        for(const [field,value] of Object.entries(setup.proposed_missing||{})){
          if(readers[field]?.setValue&&readers[field]()===null){readers[field].setValue(value);count++;}
        }
        discovery.textContent=setup.device_matched?count+" suggested fields populated. Review before Save.":
          "No native device match. Select the source entities manually.";
        tech.open=true;
      }catch(error){discovery.textContent=String(error?.message||"Native discovery unavailable");}
      finally{discover.disabled=false;}
    });
    box.append(discover,discovery,tech);
    const actions=mcEl("div","dashboard-edit-actions");
    const save=mcButton(mcTr("Add charger"),async()=>{
      const uid=id.value.trim()||name.value.trim().toLowerCase()
        .replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
      const rated=Number(power.value);
      if(!uid||!name.value.trim()||!Number.isFinite(rated)||rated<=0){
        this._settingsFeedback={status:"rejected",
          message:"Charger needs stable ID, name and positive rated kW"};
        this.showEditError(box);return;
      }
      const changes={name:name.value.trim(),kind:kind.value,rated_power_kw:rated};
      changes.control_owner=owner.value;
      const control=readSwitch();if(control)changes.control_entity=control;
      try{
        for(const [key,read] of Object.entries(readers)){
          const value=read();if(value!==null)changes[key]=value;
        }
      }catch(error){
        this._settingsFeedback={status:"rejected",message:String(error.message)};
        this.showEditError(box);return;
      }
      await this.saveSettings("charger",uid,changes,"create",true);
    });
    save.disabled=this._settingsBusy;
    actions.append(save,mcButton(mcTr("Cancel"),()=>{
      this._createCharger=false;this.render();
    }));
    box.append(actions);container.append(box);
  }
  financialSummary(container,kind,id){
    const periods=this._data.period_costs?.[kind]?.[id]||{};
    const sessions=this._data.session_costs?.[kind]?.[id]||{};
    const planned=this._data.planned_costs?.[kind]?.[id];
    if(!Object.keys(periods).length&&!Object.keys(sessions).length&&
        (!planned||planned.quality==="no_planned_energy"))return;
    const details=mcEl("div","financial-details");
    const money=(value,currency)=>typeof value==="number"&&currency?
      new Intl.NumberFormat(undefined,{style:"currency",currency}).format(value):mcTr("Unknown");
    for(const [period,label] of [["today","Charging cost today"],["month","Charging cost this month"],["year","Charging cost this year"]]){
      const row=periods[period];
      if(!row)continue;
      const partial=row.cost==null&&row.covered_cost!=null;
      const amount=money(partial?row.covered_cost:row.cost,row.currency);
      mcPair(details,mcTr(label),amount+(partial?" · "+mcTr("Partial coverage"):""));
      if(row.average_price_per_kwh!=null&&row.currency)
        details.append(mcEl("p","muted small",mcTr("Average charging price")+" · "+
          row.average_price_per_kwh.toFixed(4)+" "+row.currency+"/kWh · "+
          Number(row.covered_energy_kwh).toFixed(2)+" kWh"+(partial?" · "+mcTr("Partial coverage"):"")));
      if(row.cost==null&&row.days_expected>0)
        details.append(mcEl("p","muted small",String(row.days_available)+"/"+
          String(row.days_expected)+" "+mcTr("Days checked")));
    }
    for(const [phase,label] of [["active","Active session cost"],["last","Last session cost"]]){
      const session=sessions[phase];
      if(!session)continue;
      const partial=session.cost==null&&session.covered_cost!=null;
      const amount=money(partial?session.covered_cost:session.cost,session.currency);
      mcPair(details,mcTr(label),amount+(partial?" · "+mcTr("Partial coverage"):"")+
        (session.basis?" · "+session.basis:""));
      if(session.quality==="partial_observation")details.append(mcEl("p","muted small",mcTr("Incomplete start/end or source coverage · observed portion only")));
    }
    if(planned&&planned.quality!=="no_planned_energy")this.planCostLine(details,planned,"Planned charging cost");
    // One headline, all period/session detail available in one disclosure.
    const choice=[["Active session cost",sessions.active],["Charging cost today",periods.today],
      ["Last session cost",sessions.last],["Planned charging cost",planned]]
      .find(([,row])=>row&&(row.cost!=null||row.covered_cost!=null));
    const hint=choice?mcTr(choice[0])+" · "+money(choice[1].cost??choice[1].covered_cost,choice[1].currency)+
      (choice[1].cost==null?" · "+mcTr("Partial coverage"):""):mcTr("Unknown");
    this.disclosure(container,kind+":"+id+":finance","Charging costs",details,hint);
  }
  planCostLine(container,row,label){
    const value=typeof row.cost==="number"&&row.currency?
      new Intl.NumberFormat(undefined,{style:"currency",currency:row.currency}).format(row.cost):
      mcTr("Unknown");
    mcPair(container,mcTr(label),value);
    if(row.basis)container.append(mcEl("p","muted small",row.basis+" · "+mcTr("reference price, not an invoice")));
  }
  sessionMetrics(container,row,observed){
    const num=(v,unit,dec=2)=>typeof v==="number"&&Number.isFinite(v)?v.toFixed(dec)+" "+unit:mcTr("Unknown");
    const meter=observed?row.meter_energy_kwh:row.actual_energy_kwh;
    const derived=row.observed_energy_kwh;
    const duration=observed?row.observed_duration_minutes:(row.duration_minutes??row.elapsed_minutes);
    const avg=row.average_power_kw??(typeof meter==="number"&&duration>0?meter*60/duration:null);
    const grid=mcEl("div","session-metrics");
    const metrics=[
      [typeof meter!=="number"&&typeof derived==="number"?"Power-derived energy":"Measured energy",num(meter??derived,"kWh")],
      ["Duration",typeof duration==="number"&&duration>0&&duration<1?
        num(Math.max(1,Math.round(duration*60)),"s",0):num(duration,"min",1)],
      ["Average power",num(avg,"kW")],["Peak power",num(row.peak_power_kw,"kW")],
      [typeof row.cost==="number"?"Verified energy cost":typeof row.estimated_variable_cost==="number"?"Indicative variable energy cost":"Estimated energy cost",
        num(row.cost??row.estimated_cost??row.estimated_variable_cost,
        row.currency??row.estimated_cost_currency??row.estimated_variable_cost_currency??"")]];
    for(const [label,value] of metrics){
      const cell=mcEl("div","goal-metric");cell.append(mcEl("span","muted small",mcTr(label)),mcEl("strong","",value));grid.append(cell);
    }
    container.append(grid);
    if(typeof row.cost!=="number"&&(typeof row.estimated_cost==="number"||typeof row.estimated_variable_cost==="number"))
      container.append(mcEl("p","muted small",mcTr("Power-derived estimate, not a bill")+" · "+
        (row.estimated_cost_basis||"effective")));
    if(observed&&row.meter_observed_at)container.append(mcEl("p","muted small",
      "Meter reading · "+mcTime(row.meter_observed_at,this._data.timezone)));
    if(observed&&!row.complete_observed_window)container.append(mcEl("p","plan-caution",
      "Incomplete start/end or source coverage · observed portion only"));
  }
  observedChargerActivity(card,charger,latestOnly=false){
    const rows=(this._data.observed_sessions||[]).filter(row=>row.charger_id===charger.id)
      .sort((a,b)=>String(b.ended_at).localeCompare(String(a.ended_at)));
    if(!rows.length)return;
    const render=row=>{
      const panel=mcEl("div","session-summary");
      const fresh=this._data.observations?.chargers?.[charger.id]?.power_kw;
      const charging=row.ongoing&&fresh?.quality==="ok"&&fresh.value>0.05;
      panel.append(mcEl("strong","",charging?"Observed charging now":"Observed charging run"),
        mcEl("p","muted small",mcTime(row.started_at,this._data.timezone)+" – "+
          mcTime(row.ended_at,this._data.timezone)+" · "+mcTr("Vehicle unknown")));
      this.sessionMetrics(panel,row,true);return panel;
    };
    card.append(render(rows[0]));
    if(!latestOnly&&rows.length>1){
      const history=mcEl("div");
      for(const row of rows.slice(1))history.append(render(row));
      this.disclosure(card,"charger:"+charger.id+":observed","Earlier observed runs",history,
        (rows.length-1)+" · up to 48h");
    }
  }
  chargerSetup(card,charger){
    const setup=this._data.charger_setup?.[charger.id];
    if(!setup)return;
    const key="charger:"+charger.id+":setup";
    const proposal=setup.proposed_missing||{};
    const fields=Object.keys(proposal);
    const bounds=setup.effective_current||{};
    if(charger.kind==="variable_current"){
      const format=b=>b?.min_current_a!=null&&b?.max_current_a!=null?
        b.min_current_a+"–"+b.max_current_a+" A"+(b.current_step_a!=null?" · "+b.current_step_a+" A step":""):mcTr("Unknown");
      mcPair(card,"Effective current range",format(bounds));
      const electrical=setup.effective_electrical||{};
      if(electrical.phase_count!=null&&electrical.voltage_v!=null)
        mcPair(card,mcTr("Electrical limits & optional sources"),
          electrical.phase_count+" × "+electrical.voltage_v+" V"+
          (setup.nominal_electrical_defaults?.length?" · "+mcTr("Default"):""));
      if(this._editingField===key){
        mcPair(card,"Native device current range",format(setup.native_current));
        mcPair(card,"Configured current range",format(setup.configured_current));
      }
      if(setup.native_current?.max_current_a!=null&&bounds.max_current_a>setup.native_current.max_current_a)
        card.append(mcEl("p","plan-caution","Configured maximum exceeds native hardware range; correct the setting."));
    }
    const required=["control_entity","power_entity"];
    if(charger.kind==="variable_current")required.push("current_control_entity","connected_entity");
    const absent=required.filter(f=>!charger[f]);
    if(absent.length)card.append(mcEl("p","muted small","Unbound sources · "+
      absent.map(f=>mcTr(MC_OWNER_NAMES[f]||f)).join(", ")));
    if(this._editingField===key&&!charger.energy_entity)card.append(mcEl("p","muted small","Optional cumulative meter: power-derived energy remains available when measured coverage is sufficient."));
    if(this._editingField===key&&charger.kind==="variable_current"&&!charger.current_readback_entity)
      card.append(mcEl("p","muted small","Independent current sensor optional when qualified power readback suffices."));
    if(this._editingField!==key){
      card.append(mcButton(mcTr("Review charger setup")+(fields.length?" ("+fields.length+" "+mcTr("suggestions")+")":""),()=>{
        this._editingField=key;this._settingsFeedback=null;this.render();
      }));
      return;
    }
    const panel=mcEl("div","dashboard-field-edit");
    panel.append(mcEl("h4","","Charger setup"));
    panel.append(mcEl("p","muted small",setup.device_matched?
      "Native device matched. Review proposed sources and limits before Save.":
      "No native device match; choose sources explicitly."));
    const readers={};
    const draft={...charger,...proposal};
    const primary=mcEl("div","setup-fields");
    const advanced=mcEl("details","owner-group");
    advanced.append(mcEl("summary","","Electrical limits & optional sources"));
    const secondary=mcEl("div","setup-fields");advanced.append(secondary);
    const editable=["control_entity","connected_entity","power_entity","energy_entity","session_entity"];
    if(charger.kind==="variable_current")editable.push("current_control_entity",
      "current_readback_entity","min_current_a","max_current_a","current_step_a");
    editable.push("rated_power_kw","phase_count","voltage_v");
    for(const field of editable){
      if(Object.hasOwn(proposal,field))
        panel.append(mcEl("p","muted small","Suggested · "+mcTr(MC_OWNER_NAMES[field]||field)));
      else if((setup.candidates?.[field]||[]).length>1&&!charger[field])
        panel.append(mcEl("p","muted small","Multiple native candidates · "+
          setup.candidates[field].join(", ")));
      const target=["control_entity","connected_entity","power_entity","current_control_entity","energy_entity"].includes(field)?primary:secondary;
      readers[field]=this.dashboardFieldControl(target,"charger",draft,field);
    }
    panel.append(primary,advanced);
    const actions=mcEl("div","dashboard-edit-actions");
    const save=mcButton("Save charger setup",async()=>{
      const changes={};
      try{
        for(const [field,read] of Object.entries(readers)){
          const value=read();
          if((charger[field]??null)!==value)changes[field]=value;
        }
        if(!Object.keys(changes).length){this._editingField="";this.render();return;}
        await this.saveSettings("charger",charger.id,changes,"save",true);
      }catch(error){
        this._settingsFeedback={status:"rejected",message:String(error.message)};
        this.showEditError(panel);
      }
    });
    save.disabled=this._settingsBusy||Boolean(this._pendingSettings);
    actions.append(save,mcButton("Cancel",()=>{this._editingField="";this.render();}));
    panel.append(actions);card.append(panel);
  }
  chargers(container){
    const d=this._data,chargers=d.configuration.chargers||[],observations=(d.observations||{}).chargers||{};
    this.title(container,mcTr("Chargers")+" ("+chargers.length+")");
    this.feedback(container);
    if(!chargers.length)this.notice(container,"No charging points",false);
    if(this.canEditSettings()){
      if(this._createCharger)this.dashboardChargerCreate(container);
      else container.append(mcButton(mcTr("Add charger"),()=>{
        this._createCharger=true;this.render();
      }));
    }
    const chargerCards=mcEl("div","object-grid");container.append(chargerCards);
    for(const c of chargers){
      const obs=observations[c.id]||{};
      const card=mcEl("div","card object-card");
      card.setAttribute("data-mc-object","charger:"+c.id);
      if(this._open===c.id||this._editingField.startsWith("charger:"+c.id+":"))card.className+=" expanded";
      const head=mcEl("div","row");head.append(mcIconLabel(mcEl("h3","",c.name),c.name,c.kind==="on_off"?"power-socket-eu":"ev-station"),this.operationalIndicator(c),mcButton(this._open===c.id?"Hide details":"Details",()=>{this._open=this._open===c.id?"":c.id;this.render();}));
      card.append(head);
      const chip=mcEl("div","plan-key"),dot=mcEl("span","plan-swatch");
      dot.style.background=mcOwnerColor("charger",c.id,d.configuration,d.plan_palette);
      chip.append(dot,mcEl("span","muted small",mcTr("Plan color")+" · "+mcTr(c.plan_color||"blue")));
      card.append(chip);
      const states=(d.charger_states||{})[c.id]||{};
      const activation=c.control_owner==="multicharge"&&c.physical_commissioned!==false?"Active":"Inactive";
      const connection=states.connection_state==="asset_connected"?
        (states.connection_basis==="user_confirmed"?"Asset connected (user confirmed)":"Asset connected"):
        states.connection_state==="no_asset_connected"?"No asset connected":"Unknown";
      const activity={charging:"Charging",paused:"Paused",stopped:"Stopped"}[states.charging_session]||"Unknown";
      const readiness={ready:"Ready",waiting:"Waiting",error:"Error",unavailable:"Unavailable"}[states.charging_state]||"Unknown";
      const stateGrid=mcEl("div","charger-state-grid");
      for(const [label,value] of [["Activation",activation],["Connection state",connection],
          ["Charging session",activity],["Charging state",readiness]]){
        const cell=mcEl("div","goal-metric");
        cell.append(mcEl("span","muted small",mcTr(label)),mcEl("strong","",mcTr(value)));
        stateGrid.append(cell);
      }
      card.append(stateGrid);
      if(this._settingsFeedback?.status==="confirmed"&&this._settingsFeedback.scope==="charger"&&
          this._settingsFeedback.targetId===c.id)this.feedback(card);
      if(states.reason&&states.charging_state!=="ready")
        card.append(mcEl("p","muted small",mcReason(states.reason)));
      if(states.switch_state==="on"&&activity==="Unknown")
        card.append(mcEl("p","muted small",mcTr("Switch on · charging not measured")));
      const powerLine=mcEl("div","row charger-power");
      powerLine.append(mcEl("span","muted small",mcTr("Effective charging power")),
        mcEl("strong","value",mcValue(obs.power_kw," kW")));
      card.append(powerLine);
      this.financialSummary(card,"charger",c.id);
      if(this.canEditSettings()){
        const activationKey="charger:"+c.id+":control_owner";
        if(this._editingField===activationKey){
          if(states.switch_state==="on"||(obs.power_kw?.quality==="ok"&&obs.power_kw.value>0.05))
            card.append(mcEl("p","plan-caution",mcTr("Stop charging with the current owner before changing activation")));
          this.dashboardEditField(card,"charger",c,"control_owner");
        }else card.append(mcButton(mcTr("Change activation"),()=>{
          this._settingsFeedback=null;this._editingField=activationKey;this.render();
        }));
        this.chargerSetup(card,c);
      }
      const session=(d.active_sessions||{})[c.id];
      if(session){
        mcPair(card,"Active session",mcTime(session.started_at,d.timezone));
        this.sessionMetrics(card,session,false);
        const intent=session.requested_budget_amount!=null?
          session.requested_budget_amount+" "+
            (session.requested_budget_currency||"EUR"):
          session.requested_kwh!=null?session.requested_kwh+" kWh":
          session.requested_duration_minutes!=null?
            session.requested_duration_minutes+" "+mcTr("minutes"):
          session.soc_target!=null?session.soc_target+"%":mcTr("Not set");
        mcPair(card,mcTr("Active session goal"),intent);
        if(session.requested_budget_amount!=null){
          mcPair(card,mcTr("Indicative budget used"),
            session.budget_cost===null||session.budget_cost===undefined?
              mcTr("Unknown"):String(session.budget_cost)+" "+
                (session.requested_budget_currency||"EUR"));
          mcPair(card,mcTr("Budget measurement quality"),
            mcReason(session.budget_quality||"unknown"));
        }
      }
      this.chargerQuickSelection(card,c);
      // The owning native chooser already displays the assigned vehicle.
      const identity=(d.connection_identity||{})[c.id]||null;
      if(obs.connected?.quality==="ok"&&obs.connected.value===true&&
          (!identity||identity.asset_id!==c.asset))
        mcPair(card,mcTr("Connected vehicle"),mcTr("Vehicle unknown"));
      const history=(d.recent_completed_sessions||d.completed_sessions||[]).filter(x=>x.charger_id===c.id);
      const latest=history.length?history[history.length-1]:null;
      if(latest){
        const historyPanel=mcEl("div","history-values");
        mcPair(historyPanel,"Last confirmed session",mcTime(latest.ended_at,d.timezone));
        this.sessionMetrics(historyPanel,latest,false);
        // Cost is shown once in the shared session metrics.
        mcPair(historyPanel,mcTr("Original vehicle at session time"),
          latest.asset_id||mcTr("Anonymous charger-only session"));
        mcPair(historyPanel,mcTr("Physical STOP confirmed"),
          latest.physical_stop_confirmed===true?mcTr("Yes"):mcTr("Unknown"));
        if(latest.stop_reason)
          mcPair(historyPanel,mcTr("Session stop reason"),mcReason(latest.stop_reason));

        for(const earlier of history.slice(-4,-1).reverse()){
          const row=mcEl("div","session-summary");
          row.append(mcEl("strong","",mcTime(earlier.ended_at,d.timezone)));
          this.sessionMetrics(row,earlier,false);historyPanel.append(row);
        }
        this.disclosure(card,"charger:"+c.id+":history",
          "Last charging session",historyPanel,
          mcTime(latest.ended_at,d.timezone));
      }
      this.observedChargerActivity(card,c);
      if(this._open===c.id){
        const detail=mcEl("div","details");
        detail.append(mcEl("h4","",mcTr("Physical Charger & verified sources")));
        mcPair(detail,"Control type",c.kind==="on_off"?"On/off":"Variable current");
        mcPair(detail,"Rated power",c.rated_power_kw+" kW");
        mcPair(detail,"Phases",c.phase_count||"Unverified");
        const bounds=d.charger_setup?.[c.id]?.effective_current||c;
        mcPair(detail,"Current range",bounds.min_current_a!=null&&bounds.max_current_a!=null?
          bounds.min_current_a+"–"+bounds.max_current_a+" A":"Unknown");
        if(c.kind==="variable_current"){
          for(const [field,label] of [
            ["min_charging_power_kw","Minimum charging power"],
            ["max_charging_power_kw","Maximum charging power"],
            ["set_charging_power_kw","Set charging power"]
          ]){
            const session=(d.active_sessions||{})[c.id];
            const kw=field==="set_charging_power_kw"?
              (session?.target_current_a!=null&&c.voltage_v&&c.phase_count?
                session.target_current_a*c.voltage_v*c.phase_count/1000:null):
              c[field];
            mcPair(detail,mcTr(label),kw==null?mcTr("Not set"):Number(kw).toFixed(2)+" kW");
            this.nativeNumberEditor(detail,"charger",c.id,field,label,
              kw,"kW");
          }
        }else{
          mcPair(detail,mcTr("Charging power control"),mcTr("On/off only"));
        }
        mcPair(detail,"Source state",obs.power_kw?mcTr(obs.power_kw.quality==="ok"?"Ready":"Unavailable"):"Unknown");
        const actual=(d.command_outcomes||{})[c.id]||{};
        mcPair(detail,"Status",mcTr(actual.status==="confirmed"?"Confirmed":actual.status==="rejected"?"Rejected":actual.status==="execution_unknown"?"Unavailable":"No action"));
        if(actual.reason)mcPair(detail,"Reason",mcReason(actual.reason));
        if(actual.readback_at)mcPair(detail,"Measured confirmation",mcTime(actual.readback_at,d.timezone));
        if(this.canEditSettings())this.ownerColorControl(detail,"charger",c);
        this.ownerFacts(detail,"charger",c,["control_owner"]);
        card.append(detail);
      }
      const capability=(d.command_capabilities||{})[c.id]||{};
      const outcome=this._commandFeedback[c.id]||(d.command_outcomes||{})[c.id];
      const controls=mcEl("div","controls");
      if(this.canManage()&&capability.start_allowed){
        const start=mcButton("Start charging",()=>this.command(c.id,"start"));
        start.disabled=this._commandBusy;
        controls.append(start);
      }
      if(this.canManage()&&capability.stop_allowed){
        const stop=mcButton("Stop charging",()=>this.command(c.id,"stop"));
        stop.disabled=this._commandBusy;
        controls.append(stop);
      }
      if(this.canManage()&&capability.pause_allowed){
        const pause=mcButton(mcTr("Pause charging"),()=>this.command(c.id,"pause"));
        pause.disabled=this._commandBusy;
        controls.append(pause);
      }
      if(this.canManage()&&capability.resume_allowed){
        const resume=mcButton(mcTr("Resume charging"),()=>this.command(c.id,"resume"));
        resume.disabled=this._commandBusy;
        controls.append(resume);
      }
      if(controls.children.length)card.append(controls);
      if(this.canManage()&&!c.asset){
        // One user goal, one input, one command. All readiness is server-owned.
        const oneOff=mcEl("div","details");

        const draft=this._manualDrafts[c.id]||{kind:"duration",duration:"",energy:"",budget:""};
        this._manualDrafts[c.id]=draft;
        const goal=this.field(oneOff,mcTr("Charging goal"),draft.kind,null,[
          ["duration",mcTr("Time limit (minutes)")],
          ["energy",mcTr("Energy limit (kWh)")],
          ["budget",mcTr("Budget limit (€)")]
        ]);
        const labels={duration:"Time limit (minutes)",energy:"Energy limit (kWh)",budget:"Budget limit (€)"};
        const amount=this.field(oneOff,mcTr(labels[draft.kind]),draft[draft.kind],"number");
        amount.setAttribute("min",draft.kind==="duration"?"1":"0.01");
        amount.setAttribute("step",draft.kind==="duration"?"1":"any");
        goal.addEventListener("change",()=>{
          draft.kind=goal.value;
          this.render();
        });
        const valid=()=>{
          const value=Number(amount.value);
          return !!amount.value.trim()&&Number.isFinite(value)&&value>0&&
            (draft.kind!=="duration"||(Number.isInteger(value)&&value<=1440))&&
            (draft.kind!=="energy"||value<=1000)&&(draft.kind!=="budget"||value<=10000);
        };
        const reason=capability.manual_goal_reasons?.[draft.kind]||
          capability.manual_one_off_reason||"SOURCE_NOT_SELECTED";
        const submit=mcButton(mcTr("Start bounded session"),()=>{
          if(reason!=="READY"||!valid())return;
          const value=Number(amount.value);
          this.command(c.id,"start",draft.kind==="duration"?{duration_minutes:value}:
            draft.kind==="energy"?{energy_kwh:value}:{cost_amount:value,currency:"EUR"});
        });
        const availability=mcEl("p","muted small");
        const updateGoal=()=>{
          submit.disabled=this._commandBusy||reason!=="READY"||!valid();
          availability.textContent=reason==="READY"?"":mcTr("Start unavailable")+" · "+mcReason(reason);
        };
        amount.addEventListener("input",()=>{draft[draft.kind]=amount.value;updateGoal();});
        updateGoal();
        oneOff.append(submit,availability);
        this.disclosure(card,"charger:"+c.id+":one-off","Manual one-off charge",oneOff,
          reason==="READY"?"":mcTr("Start unavailable")+" · "+mcReason(reason));
      }
      if(!capability.start_allowed && capability.reason && c.asset)
        card.append(mcEl("p","muted small",mcTr("Unavailable")+" · "+mcReason(capability.reason)));
      if(outcome){
        const bad=outcome.status==="rejected"||outcome.status==="execution_unknown";
        const label=bad?mcReason(outcome.reason):outcome.status==="confirmed"?
          (outcome.reason==="NATIVE_SWITCH_STATE"?(outcome.action==="start"?mcTr("Switch on · charging not measured"):mcTr("Switch off · charging not measured")):
           outcome.action==="stop"?"Stopped":
           outcome.action==="pause"?mcTr("Paused"):
           outcome.action==="resume"?mcTr("Ready for next plan"):"Command confirmed"):"Pending";
        const status=mcEl("p","small"+(bad?" error":""),label);
        status.setAttribute("role",bad?"alert":"status");
        card.append(status);
      }
      chargerCards.append(card);
    }
  }

  openYamlEditor(){
    if(!this._data)return;
    this._yamlEditorOpen=true;
    this._yamlBaselineRevision=this._data.configuration_revision;
    this._yamlCommittedRevision=null;
    this.render();
  }
  yamlEditor(container){
    if(!this._yamlEditorOpen||!this._data)return;
    const panel=mcEl("section","yaml-editor");
    panel.append(mcEl("h3","","Complete site configuration · YAML / JSON"));
    const editor=mcEl("textarea","");
    editor.setAttribute("aria-label","YAML or JSON configuration");
    editor.setAttribute("spellcheck","false");
    editor.setAttribute("rows","22");
    editor.value=JSON.stringify(this._data.configuration,(key,value)=>key==="physical_commissioned"?undefined:value,2);
    const notice=mcEl("p","message");
    notice.setAttribute("role","status");
    const buttons=mcEl("div","yaml-actions");
    editor.addEventListener("input",()=>{
      notice.textContent="";
      notice.setAttribute("role","status");
    });
    const save=mcButton("Save",async ()=>{
      if(this._settingsBusy)return;
      this._settingsBusy=true;
      save.disabled=true;
      notice.textContent="Saving…";
      try{
        const result=await this._hass.callWS({
          type:"robotix_multicharge/yaml_configuration",
          yaml_text:editor.value,
          expected_revision:this._yamlBaselineRevision
        });
        if(result.status!=="accepted_unconfirmed"||!result.expected_revision)
          throw Error("Save not accepted");
        this._yamlCommittedRevision=result.expected_revision;
        this._settingsFeedback={status:"accepted_unconfirmed",message:"Pending"};
        this._last=0;
        await this.load();
        if(!this._yamlCommittedRevision){
          // An explicit Save is the only reason to close a focused editor.
          this.render();
          return;
        }
        notice.textContent="Save accepted; Home Assistant readback pending. Refresh to verify.";
      }catch(error){
        this._yamlCommittedRevision=null;
        const reason=String(error?.message||error?.code||"Unavailable");
        mcIconLabel(notice,"Save rejected: "+reason,"alert-circle-outline","bad");
        notice.setAttribute("role","alert");
      }finally{
        this._settingsBusy=false;
        save.disabled=false;
      }
    });
    const cancel=mcButton("Cancel",()=>{
      this._yamlEditorOpen=false;
      this._yamlCommittedRevision=null;
      this._yamlBaselineRevision=null;
      this.render();
    });
    buttons.append(save,cancel);
    panel.append(editor,buttons,notice);
    container.append(panel);
  }
  settings(container){
    const d=this._data,c=d.configuration||{},ctl=c.controller||{};
    this.title(container,"Settings");
    const toolbar=mcEl("div","settings-toolbar");
    toolbar.append(mcButton(this._yamlEditorOpen?"Close YAML editor":"Edit YAML",()=>{
      if(this._yamlEditorOpen){
        this._yamlEditorOpen=false;
        this._yamlCommittedRevision=null;
        this.render();
      }else this.openYamlEditor();
    }));
    container.append(toolbar);
    if(this._yamlEditorOpen)this.yamlEditor(container);
    if(d.configuration_managed_by_yaml)mcPair(
      container,"Configuration",
      "Legacy file-owned configuration is read-only; migrate once to GUI ownership"
    );
    this.feedback(container);
    const settingsGrid=mcEl("div","settings-grid");
    for(const title of MC_SETTINGS){
      const primary=["Charging site","Charging strategy","Sources & bindings"].includes(title);
      const open=primary||title===this._settingsOpen;
      const group=mcEl("section","card settings-card"+(open?" expanded":""));
      const heading=mcEl("div","settings-heading");
      heading.append(mcIconLabel(mcEl("h3","",title),title,mcIconFor(title)));
      const summary=title==="Charging site"?ctl.name||"Not set":
        title==="Sources & bindings"?[ctl.price_entity||ctl.current_price_entity?"Tariff":null,
          ctl.solar_entity||ctl.solar_power_entity||ctl.solar_surplus_entity?"Solar":null,
          ctl.home_power_entity?"Home":null,
          ctl.grid_power_entity?"Grid":null,
          ctl.binding_entity?"Capacity":null].filter(Boolean).join(" · ")||"No source":
        title==="Charging strategy"?ctl.mode||"Off":
        title==="Safety & limits"?(ctl.max_power_kw===undefined?"No capacity":ctl.max_power_kw+" kW")+" · "+(ctl.max_parallel||1)+" parallel":
        title==="Integrations"?(c.chargers||[]).length+" chargers":
        d.configuration_managed_by_yaml?"Legacy file source · read-only":"One dashboard-owned configuration";
      heading.append(mcEl("p","muted small",summary));
      const row=mcEl("div","row");
      row.append(heading);
      if(!primary)row.append(mcButton(open?"Close":"Details",()=>{
        this._settingsOpen=open?"":title;this.render();
      }));
      group.append(row);
      if(open){
        const detail=mcEl("div","details");
        if(title==="Charging site"){
          mcPair(detail,"Site name",ctl.name);
          mcPair(detail,mcTr("Site controller ID"),ctl.id);
          if(this.canEditSettings()&&this.ownerEntity("controller",ctl.id,"name")){
            const rename=mcEl("div","row");
            rename.append(mcEl("span","",mcTr("Site name")),
              mcButton("Edit",()=>this.openNative("controller",ctl.id,"name")));
            detail.append(rename);
          }
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_parallel",
            "Parallel chargers",ctl.max_parallel);
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_power_kw",
            "Maximum group power",ctl.max_power_kw,"kW");
          this.nativeNumberEditor(detail,"controller",ctl.id,"power_adjustment_interval_minutes",
            "Power adjustment interval",ctl.power_adjustment_interval_minutes??5,"min");
          this.ownerFacts(detail,"controller",ctl,[
            "solar_power_entity","home_power_entity","grid_power_entity","solar_surplus_entity",
            "current_price_entity","price_entity","export_price_entity","solar_entity",
            "site_power_entity","binding_entity","phase_limits_a"
          ]);
        }else if(title==="Charging strategy"){
          const options=mcEl("div","chips");
          for(const mode of this.canEditSettings()?MC_MODES:[]){
            const btn=mcButton(mode,()=>this.nativeSelect("controller",ctl.id,"mode",mode));
            btn.disabled=this._settingsBusy||mode===ctl.mode||
              !this.ownerEntity("controller",ctl.id,"mode");
            if(mode===ctl.mode)btn.className="active";
            options.append(btn);
          }
          detail.append(options);
          if(!this.canEditSettings())mcPair(detail,"Charging mode",ctl.mode||"Unknown");
        }else if(title==="Sources & bindings"){
          detail.append(mcEl("h4","",mcTr("Site energy configuration")));
          detail.append(mcEl("p","muted small",mcTr("Select your import price sensor. Forecast intervals are detected automatically; use a separate forecast source only when needed.")));
          const price=d.observations?.sources||{};
          mcPair(detail,"Forecast source",price.tariff_source||mcTr("Not set"));
          mcPair(detail,"Forecast intervals",price.tariff_slot_count??0);
          mcPair(detail,"Prices available until",price.tariff_coverage_until?mcTime(price.tariff_coverage_until,d.timezone):mcTr("Unknown"));
          mcPair(detail,"Tariff",mcReason(price.tariff_quality));
          if(price.tariff_tomorrow_quality)mcPair(detail,"Tomorrow",price.tariff_tomorrow_quality==="OK"?mcTr("Ready"):mcReason(price.tariff_tomorrow_quality));
          const solarMode=ctl.solar_source_kind||
            (ctl.solar_entity?"intervals":"none");
          mcPair(detail,mcTr("Solar source type"),mcTr(solarMode));
          mcPair(detail,mcTr("Grid meter direction"),
            mcTr(ctl.grid_power_direction||"import_positive"));
          if(this.canEditSettings()){
            for(const [field,caption,choices] of [
              ["solar_source_kind","Solar source type (native)",[
                ["none",mcTr("Not configured")],
                ["intervals",mcTr("Qualified Solar intervals")],
                ["grid_export",mcTr("Measured grid export")],
                ["direct_surplus",mcTr("Measured solar surplus")]
              ]],
              ["grid_power_direction","Grid meter direction (native)",[
                ["import_positive",mcTr("Import is positive")],
                ["export_positive",mcTr("Export is positive")]
              ]]
            ]){
              if(!this.ownerEntity("controller",ctl.id,field))continue;
              const value=field==="solar_source_kind"?solarMode:
                ctl.grid_power_direction||"import_positive";
              const select=this.field(detail,mcTr(caption),value,null,choices);
              select.disabled=this._settingsBusy;
              select.addEventListener("change",()=>{
                if(field==="solar_source_kind"&&
                  (select.value==="intervals"&&!ctl.solar_entity||
                   select.value==="grid_export"&&!ctl.grid_power_entity||
                   select.value==="direct_surplus"&&!ctl.solar_surplus_entity)){
                  this._settingsFeedback={status:"rejected",
                    message:mcTr("Select the required native meter before enabling this Solar mode")};
                  this.render();return;
                }
                void this.nativeSelect("controller",ctl.id,field,select.value);
              });
            }
          }
          const advancedSources=mcEl("div","owner-fields");
          const advancedFields=["solar_surplus_entity","export_price_entity","solar_entity","site_power_entity","binding_entity"];
          for(const [field,label] of [
            ["current_price_entity","Current import price"],
            ["price_entity","Future tariff intervals"],
            ["solar_power_entity","Solar production"],
            ["home_power_entity","Home consumption"],
            ["grid_power_entity","Grid power"],
            ["solar_surplus_entity","Solar surplus"],
            ["export_price_entity","Current export price"],
            ["solar_entity","Solar intervals"],
            ["site_power_entity","Site power"],["binding_entity","Capacity"]
          ]){
            const parent=advancedFields.includes(field)?advancedSources:detail;
            const sourceRow=mcEl("div","row");
            sourceRow.append(mcEl("span","",mcTr(label)),mcEl("span","muted small",ctl[field]||mcTr("Not set")));
            if(this.canEditSettings()){
              const key="controller:"+ctl.id+":"+field;
              sourceRow.append(
                mcButton(mcTr("Edit"),()=>{
                  this._editingField=this._editingField===key?"":key;this.render();
                }));
              parent.append(sourceRow);
              if(this._editingField===key)
                this.dashboardEditField(parent,"controller",ctl,field);
            }else parent.append(sourceRow);
          }
          const advancedKey="controller:"+ctl.id+":advanced-sources";
          if(advancedFields.some(field=>this._editingField==="controller:"+ctl.id+":"+field))
            this._folds[advancedKey]=true;
          this.disclosure(detail,advancedKey,"Advanced source bindings",advancedSources);
        }else if(title==="Safety & limits"){
          mcPair(detail,"Maximum group kW",
            ctl.max_power_kw===undefined?"Unknown":ctl.max_power_kw+" kW");
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_power_kw",
            "Maximum group power",ctl.max_power_kw,"kW");
          this.nativeNumberEditor(detail,"controller",ctl.id,"max_parallel",
            "Parallel chargers",ctl.max_parallel);
          const phaseValues=Object.entries(ctl.phase_limits_a||{});
          mcPair(detail,"Electrical limits",phaseValues.length?
            phaseValues.map(([id,amps])=>id+": "+amps+" A").join(" · "):
            mcTr("Not set"));
          if(this.canEditSettings()){
            const key="controller:"+ctl.id+":phase_limits_a";
            const row=mcEl("div","row");
            row.append(mcEl("span","muted small","Phase and circuit limits"),
              mcButton(mcTr("Edit"),()=>{
                this._editingField=key;this.render();
              }));
            detail.append(row);
            if(this._editingField===key)
              this.dashboardEditField(detail,"controller",ctl,"phase_limits_a");
          }
        }else if(title==="Integrations"){
          const tariff=d.observations?.sources||{};
          mcPair(detail,"Tariff",mcReason(tariff.tariff_quality));
          if(tariff.tariff_tomorrow_quality)mcPair(detail,"Tomorrow",tariff.tariff_tomorrow_quality==="OK"?mcTr("Ready"):mcReason(tariff.tariff_tomorrow_quality));
          mcPair(detail,"Forecast source",tariff.tariff_source||mcTr("Not set"));
          mcPair(detail,"Forecast intervals",tariff.tariff_slot_count??0);
          mcPair(detail,"Forecast price basis",tariff.tariff_basis||mcTr("Unknown"));
          mcPair(detail,"Prices available until",tariff.tariff_coverage_until?mcTime(tariff.tariff_coverage_until,d.timezone):mcTr("Unknown"));
          mcPair(detail,"Solar",mcReason((d.observations||{}).sources?.solar_quality));
          mcPair(detail,"Capacity",mcReason((d.observations||{}).sources?.binding_quality));
          for(const [field,label,unit] of [
            ["solar_power","Solar production","kW"],
            ["home_power","Home consumption","kW"],
            ["grid_power","Grid power","kW"],
            ["available_solar_kw","Available surplus","kW"],
            ["current_export_price","Current export price",""]
          ]){
            const reading=(d.observations||{}).sources?.[field];
            mcPair(detail,label,reading?.quality==="ok"||reading?.quality==="OK"?
              String(reading.value)+(unit?" "+unit:"") : mcTr("Unknown"));
          }
          mcPair(detail,"Solar source",ctl.solar_source_kind||"none");
          mcPair(detail,"Grid direction",ctl.grid_power_direction||"import_positive");
        }
        group.append(detail);
      }
      settingsGrid.append(group);
    }
    container.append(settingsGrid);
  }
}
if(!customElements.get("robotix-multicharge-card"))customElements.define("robotix-multicharge-card",RobotixMultiChargeCard);

/* Native HA sidebar view: reuse the one source-backed card and its five tabs.
 * No second state store, permissions model, or physical command channel.
 */
class RobotixMultiChargePanel extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    const style=document.createElement("style");
    style.textContent=`
      :host { display:block; min-height:100%; box-sizing:border-box; }
      .panel { max-width:1440px; margin:0 auto; padding:16px;
               box-sizing:border-box; }
      robotix-multicharge-card { display:block; width:100%; }
      @media (max-width:600px) { .panel { padding:8px; } }
    `;
    this._content=document.createElement("main");
    this._content.className="panel";
    this._card=document.createElement("robotix-multicharge-card");
    this._card.setConfig({});
    this._content.append(this._card);
    this.shadowRoot.append(style,this._content);
  }
  set hass(value){
    this._hass=value;
    this._card.hass=value;
  }
  get hass(){return this._hass;}
  set panel(value){this._panel=value;}
  get panel(){return this._panel;}
  set narrow(value){this._narrow=value;}
  get narrow(){return this._narrow;}
  disconnectedCallback(){
    if(typeof this._card.disconnectedCallback==="function"){
      this._card.disconnectedCallback();
    }
  }
}
if(!customElements.get("robotix-multicharge-panel")){
  customElements.define("robotix-multicharge-panel",RobotixMultiChargePanel);
}

window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="robotix-multicharge-card")){
  window.customCards.push({type:"robotix-multicharge-card",name:"Robotix MultiCharge",description:"Charging plan"});
}