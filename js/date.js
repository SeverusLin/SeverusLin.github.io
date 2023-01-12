function time(){
    var vWeek,vWeek_s,vMonth;
    vWeek = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
    vMonth = ["Jan.","Feb.","Mar.","Apr.","May","Jun.","Jul.","Aug.","Sept.","Oct.","Nov.","Dec."]
    var date =  new Date();
    year = date.getFullYear();
    month = date.getMonth();
    day = date.getDate();
    vWeek_s = date.getDay();
    var suffix;
    if(day==1||day==21||day==31){
        suffix="st";
    }
    else if(day==2||day==22){
        suffix="nd";
    }
    else if(day==3||day==23){
        suffix="rd";
    }
    else{
        suffix="th";
    }
    document.getElementById("time").innerHTML = year + " " + vMonth[month] + " " + day + suffix+ "," + "\t\t" + vWeek[vWeek_s] ;

    
    
    };
    setInterval("time()",1000);