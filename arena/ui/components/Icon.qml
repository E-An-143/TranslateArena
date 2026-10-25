import QtQuick
Canvas {
    id: icon
    property string name: "plus"
    property color color: Theme.text
    property real stroke: 1.7
    implicitWidth: 20; implicitHeight: 20
    onNameChanged: requestPaint()
    onColorChanged: requestPaint()
    onStrokeChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        let c = getContext("2d"); c.reset(); c.scale(width / 24, height / 24)
        c.strokeStyle = color; c.lineWidth = stroke; c.lineCap = "round"; c.lineJoin = "round"
        function path(points) { c.beginPath(); c.moveTo(points[0][0], points[0][1]); for(let i=1;i<points.length;i++) c.lineTo(points[i][0],points[i][1]); c.stroke() }
        function circle(x,y,r) { c.beginPath(); c.arc(x,y,r,0,Math.PI*2); c.stroke() }
        switch(name) {
        case "plus": path([[12,5],[12,19]]); path([[5,12],[19,12]]); break
        case "arrow": path([[5,12],[19,12]]); path([[14,7],[19,12],[14,17]]); break
        case "swap": path([[4,8],[20,8],[16,4]]); path([[20,16],[4,16],[8,20]]); break
        case "chevron": path([[9,6],[15,12],[9,18]]); break
        case "down": path([[6,9],[12,15],[18,9]]); break
        case "close": path([[6,6],[18,18]]); path([[18,6],[6,18]]); break
        case "check": path([[5,12],[10,17],[19,7]]); break
        case "copy": c.strokeRect(8,8,12,12); path([[15,4],[4,4],[4,15]]); break
        case "folder": path([[3,7],[10,7],[12,10],[21,10],[21,20],[3,20],[3,7]]); break
        case "home": path([[3,11],[12,3],[21,11]]); path([[5,10],[5,21],[10,21],[10,15],[14,15],[14,21],[19,21],[19,10]]); break
        case "settings": circle(12,12,4); for(let i=0;i<8;i++){ let a=i*Math.PI/4;c.beginPath();c.moveTo(12+8*Math.cos(a),12+8*Math.sin(a));c.lineTo(12+10*Math.cos(a),12+10*Math.sin(a));c.stroke() } circle(12,12,8); break
        case "history": circle(12,12,8); path([[12,7],[12,12],[16,14]]); break
        case "refresh": c.beginPath();c.arc(12,12,8,0.6,5.8);c.stroke();path([[16,3],[20,7],[21,2]]); break
        case "regenerate":
            // A single thin clockwise arc and a small open arrowhead.
            c.beginPath(); c.arc(12,12,7.5,0,Math.PI*1.75); c.stroke()
            let tipX=12+7.5*Math.SQRT1_2, tipY=12-7.5*Math.SQRT1_2
            path([[tipX-4,tipY],[tipX,tipY],[tipX,tipY-4]])
            break
        case "expand": path([[9,4],[4,4],[4,9]]); path([[15,4],[20,4],[20,9]]); path([[4,15],[4,20],[9,20]]); path([[20,15],[20,20],[15,20]]); break
        case "judge": path([[12,3],[12,20],[7,20],[17,20]]); path([[4,7],[20,7]]); path([[5,7],[2,14],[8,14],[5,7]]); path([[19,7],[16,14],[22,14],[19,7]]); break
        case "trophy":
            c.beginPath(); c.moveTo(7,3); c.lineTo(17,3); c.lineTo(17,8)
            c.bezierCurveTo(17,12,15,14,12,14); c.bezierCurveTo(9,14,7,12,7,8)
            c.closePath(); c.stroke()
            c.beginPath(); c.moveTo(7,5); c.lineTo(3,5); c.lineTo(3,7); c.quadraticCurveTo(3,11,8,11); c.stroke()
            c.beginPath(); c.moveTo(17,5); c.lineTo(21,5); c.lineTo(21,7); c.quadraticCurveTo(21,11,16,11); c.stroke()
            path([[12,14],[12,18]]); path([[8,21],[8,18],[16,18],[16,21]]); path([[6,21],[18,21]])
            break
        case "spark": path([[12,3],[14.8,9.2],[21,12],[14.8,14.8],[12,21],[9.2,14.8],[3,12],[9.2,9.2],[12,3]]); break
        case "bolt": path([[13,2],[5,13],[11,13],[10,22],[19,10],[13,10],[13,2]]); break
        case "stop": c.strokeRect(6,6,12,12); break
        case "info": circle(12,12,9); path([[12,11],[12,17]]); circle(12,7,0.2); break
        case "key": circle(8,8,5); path([[12,12],[21,21],[21,17],[17,17]]); break
        case "translate": path([[3,6],[13,6]]); path([[8,3],[8,6]]); path([[5,6],[6,11],[12,15]]); path([[11,6],[10,11],[4,15]]); path([[13,21],[17,10],[21,21]]); path([[15,17],[19,17]]); break
        }
    }
}
