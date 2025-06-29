import { Tooltip, IconButton } from '@douyinfe/semi-ui';
import { IconGridRectangle } from '@douyinfe/semi-icons';

export const MinimapSwitch = (props: {
  minimapVisible: boolean;
  setMinimapVisible: (visible: boolean) => void;
}) => {
  const { minimapVisible, setMinimapVisible } = props;

  return (
    <Tooltip content="Minimap">
      <IconButton
        theme="borderless"
        icon={
          <IconGridRectangle
            style={{
              color: minimapVisible ? undefined : '#060709cc',
            }}
          />
        }
        onClick={() => {
          setMinimapVisible(Boolean(!minimapVisible));
        }}
      />
    </Tooltip>
  );
};
