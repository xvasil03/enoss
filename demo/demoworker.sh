cd /enoss/demo

echo "Waiting Swift and OpenIO to load"
sleep 120

echo "Executing demo for Swift"
bash demo-swift.sh

echo "Executing demo for OpenIO"
bash demo-openio.sh

echo "Now sleeping - connect to me via ssh and interact with Swift and OpenIO SDS"
sleep 66666666666
